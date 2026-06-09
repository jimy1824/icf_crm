import { configureStore } from '@reduxjs/toolkit';
import authSlice from './authSlice.js';
import uiSlice from './uiSlice.js';
import clientSlice from './clientSlice.js';

export const store = configureStore({
  reducer: {
    auth:   authSlice,
    ui:     uiSlice,
    client: clientSlice,
  },
});
