import { createSlice } from '@reduxjs/toolkit';

// Tracks the currently selected client/lead context for cross-component use
const clientSlice = createSlice({
  name: 'client',
  initialState: {
    selected: null,       // { id, name, type: 'lead'|'client' }
    kanbanFilters: {
      advisor: '',
      campaign: '',
      stage: '',
    },
    leadFilters: {
      search: '',
      status: '',
      source: '',
      advisor: '',
    },
  },
  reducers: {
    setSelectedClient: (state, { payload }) => { state.selected = payload; },
    clearSelectedClient: (state) => { state.selected = null; },
    setKanbanFilter: (state, { payload }) => {
      state.kanbanFilters = { ...state.kanbanFilters, ...payload };
    },
    setLeadFilter: (state, { payload }) => {
      state.leadFilters = { ...state.leadFilters, ...payload };
    },
    resetLeadFilters: (state) => {
      state.leadFilters = { search: '', status: '', source: '', advisor: '' };
    },
  },
});

export const {
  setSelectedClient, clearSelectedClient,
  setKanbanFilter, setLeadFilter, resetLeadFilters,
} = clientSlice.actions;
export default clientSlice.reducer;
