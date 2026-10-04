// A tiny observable store (observer pattern): views subscribe and re-render when state changes.

export function createStore(initialState) {
  const state = { ...initialState };
  const listeners = new Set();
  return {
    state,
    /** Merge `changes` into the state and notify subscribers with the changed keys. */
    update(changes, details = {}) {
      Object.assign(state, changes);
      listeners.forEach((listener) => listener(state, Object.keys(changes), details));
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
