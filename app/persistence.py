"""Browser-local persistence of user progress.

All per-user progress lives in ``st.session_state`` (seeded in the init block of
``streamlit_app.py``). That is wiped whenever the page is refreshed, the
websocket drops, or the Community Cloud container restarts - which is painful in
a teaching tool where a full run takes a while. To survive those, we mirror the
small, durable slice of session state into the browser's ``localStorage`` and
restore it on load.

Only a tiny, JSON-serialisable slice is persisted: a short ``pages_visited``
list, one ``user_notes`` string, and a handful of ``{"What", "Site"}`` dicts /
booleans for the per-page site choices. All heavy geodata lives in cross-session
``@st.cache_*`` and is never part of this snapshot.

Everything funnels through a small ``ProgressStore`` seam so a server-backed
store (e.g. Supabase, for cross-device resume) could replace ``BrowserStore``
later without changing the call sites in ``streamlit_app.py`` or the reset
button. If the optional ``streamlit-local-storage`` component is not installed,
``get_store()`` returns a ``NullStore`` and the app runs exactly as before, just
without persistence.
"""

from __future__ import annotations

import json
from typing import Protocol

import streamlit as st

from app.utils import SITE_SELECTION_SUBMITTABLE

# Bump this if the shape of the persisted data changes in a way that makes old
# blobs unsafe to restore - restore() then discards mismatched versions.
SCHEMA_VERSION = 1

# The single localStorage key holding the whole JSON blob.
STORAGE_KEY = "cdc_progress_v1"

# The page the user is currently on, persisted so a refresh/crash can return
# them there instead of dumping them back on the Homepage.
CURRENT_PAGE_KEY = "current_page"

# Session-state bookkeeping keys (not themselves persisted).
_HYDRATED_FLAG = "_progress_hydrated"
_READ_ATTEMPTS = "_progress_read_attempts"
_LAST_SAVED_HASH = "_progress_last_saved"
_STORE_HANDLE = "_progress_store"
_PAGE_RESTORED = "_progress_page_restored"


def progress_keys() -> list[str]:
    """The session-state keys that make up a user's durable progress."""
    keys = ["pages_visited", "user_notes", CURRENT_PAGE_KEY]
    for i in SITE_SELECTION_SUBMITTABLE:
        keys.append(f"confirmed_site_{i}")
        keys.append(f"site_submitted_{i}")
    return keys


def snapshot() -> dict:
    """Read the durable slice of session state into a plain dict."""
    return {k: st.session_state[k] for k in progress_keys() if k in st.session_state}


def restore(data: dict) -> None:
    """Write a previously-saved snapshot back into session state."""
    for k in progress_keys():
        if k in data:
            st.session_state[k] = data[k]


#############################
# MARK: Store implementations
#############################
class ProgressStore(Protocol):
    def read(self) -> dict | None: ...
    def write(self, data: dict) -> None: ...
    def clear(self) -> None: ...


class NullStore:
    """Used when the localStorage component is unavailable - persistence off."""

    def read(self) -> dict | None:
        return None

    def write(self, data: dict) -> None:
        pass

    def clear(self) -> None:
        pass


class BrowserStore:
    """Persists the JSON blob in the browser via ``streamlit-local-storage``.

    The component instance is created once per script run (it renders a hidden
    element) and reused for read/write/clear within that run.
    """

    def __init__(self, local_storage):
        self._ls = local_storage

    def read(self) -> dict | None:
        raw = self._ls.getItem(STORAGE_KEY)
        if not raw:
            return None
        try:
            blob = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(blob, dict) or blob.get("v") != SCHEMA_VERSION:
            return None
        data = blob.get("data")
        return data if isinstance(data, dict) else None

    def write(self, data: dict) -> None:
        payload = json.dumps({"v": SCHEMA_VERSION, "data": data})
        # A distinct component key keeps the setter separate from the getter.
        self._ls.setItem(STORAGE_KEY, payload, key="cdc_progress_set")

    def clear(self) -> None:
        # deleteItem pops from its internal cache without a default, so guard
        # against clearing when nothing was ever stored (e.g. reset on a fresh
        # session).
        try:
            self._ls.deleteItem(STORAGE_KEY)
        except KeyError:
            pass


def get_store() -> ProgressStore:
    """Build the per-run store, falling back to a no-op if the component is
    missing so the app still runs before the dependency is installed."""
    try:
        from streamlit_local_storage import LocalStorage
    except ImportError:
        return NullStore()

    store = BrowserStore(LocalStorage())
    # Stash so pages rendered inside pg.run() (e.g. the reset button) can reuse
    # the same component instance instead of creating a duplicate.
    st.session_state[_STORE_HANDLE] = store
    return store


#############################
# MARK: Session integration
#############################
def load_into_session(store: ProgressStore) -> None:
    """Restore a saved snapshot onto session state, at most once per session.

    The localStorage component can return ``None`` on the first script run while
    it mounts, then return the stored value on the automatic rerun. We therefore
    give it up to two runs to surface an existing blob before treating the
    session as genuinely fresh - otherwise a returning user's progress would be
    missed. The only window this leaves is the first ~2 rerun cycles at page
    load, before the user interacts.
    """
    if st.session_state.get(_HYDRATED_FLAG):
        return

    data = store.read()
    if data:
        restore(data)
        st.session_state[_HYDRATED_FLAG] = True
        return

    attempts = st.session_state.get(_READ_ATTEMPTS, 0) + 1
    st.session_state[_READ_ATTEMPTS] = attempts
    if attempts >= 2:
        st.session_state[_HYDRATED_FLAG] = True


def save(store: ProgressStore) -> None:
    """Write the current snapshot to the store, but only when it has changed
    (so an unchanged rerun does not trigger a needless component round-trip)."""
    if not st.session_state.get(_HYDRATED_FLAG):
        # Don't persist until we've had a chance to load, or we could overwrite
        # an existing blob with fresh defaults before it's been read back.
        return

    data = snapshot()
    digest = json.dumps(data, sort_keys=True, default=str)
    if st.session_state.get(_LAST_SAVED_HASH) == digest:
        return

    store.write(data)
    st.session_state[_LAST_SAVED_HASH] = digest


def maybe_restore_page(current_page, pages_by_path: dict) -> None:
    """After progress is restored, return the user to the page they were on.

    Streamlit starts a fresh session on refresh/crash and doesn't reliably route
    back to the page the user had navigated to, so we do it explicitly - once,
    and only after hydration has actually populated ``current_page`` (which can
    take a second run while the localStorage component mounts). ``current_page``
    is a ``StreamlitPage`` and ``pages_by_path`` maps ``url_path`` -> page.
    """
    if not st.session_state.get(_HYDRATED_FLAG):
        return
    if st.session_state.get(_PAGE_RESTORED):
        return
    st.session_state[_PAGE_RESTORED] = True

    saved = st.session_state.get(CURRENT_PAGE_KEY)
    if saved and saved != current_page.url_path:
        target = pages_by_path.get(saved)
        if target is not None:
            st.switch_page(target)


def record_current_page(current_page) -> None:
    """Remember which page is being shown, so it can be restored next session."""
    st.session_state[CURRENT_PAGE_KEY] = current_page.url_path


def reset_progress(store: ProgressStore | None = None) -> None:
    """Clear the user's progress from both session state and the browser."""
    if store is None:
        store = st.session_state.get(_STORE_HANDLE) or NullStore()

    for k in progress_keys():
        st.session_state.pop(k, None)
    st.session_state.pop(_LAST_SAVED_HASH, None)
    store.clear()


def render_reset_button(
    label: str = "Start over",
    key: str = "reset_progress",
    icon: str = ":material/restart_alt:",
) -> None:
    """A confirm-gated control that wipes progress and returns to the Homepage.

    Reuses the single per-run store stashed by ``get_store()`` so it does not
    create a duplicate localStorage component.
    """

    with st.bottom.popover(label, width="stretch", icon=icon):
        st.write(
            "This will erase everything you've done so far and take you back to "
            "the start. This cannot be undone."
        )
        if st.button(
            "Yes, clear my progress and restart",
            key=f"{key}_confirm",
            type="primary",
            width="stretch",
        ):
            reset_progress()
            st.switch_page("app/Homepage.py")
