import { useDispatch, useSelector } from 'react-redux';
import { useEffect } from 'react';
import { toggleTheme } from '../store/uiSlice.js';

export function useTheme() {
  const theme = useSelector((s) => s.ui.theme);
  const dispatch = useDispatch();

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  return { theme, toggle: () => dispatch(toggleTheme()) };
}
