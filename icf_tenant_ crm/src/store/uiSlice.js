import { createSlice } from '@reduxjs/toolkit';

const getInitialTheme = () => {
  const saved = localStorage.getItem('crm_theme');
  if (saved) return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

const uiSlice = createSlice({
  name: 'ui',
  initialState: {
    theme:           getInitialTheme(),
    sidebarCollapsed: false,
    commandPaletteOpen: false,
    notificationCount:  0,
  },
  reducers: {
    toggleTheme: (state) => {
      state.theme = state.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('crm_theme', state.theme);
      document.documentElement.classList.toggle('dark', state.theme === 'dark');
    },
    setSidebarCollapsed: (state, { payload }) => { state.sidebarCollapsed = payload; },
    toggleCommandPalette: (state) => { state.commandPaletteOpen = !state.commandPaletteOpen; },
    setCommandPalette: (state, { payload }) => { state.commandPaletteOpen = payload; },
    setNotificationCount: (state, { payload }) => { state.notificationCount = payload; },
  },
});

export const {
  toggleTheme, setSidebarCollapsed, toggleCommandPalette,
  setCommandPalette, setNotificationCount,
} = uiSlice.actions;
export default uiSlice.reducer;
