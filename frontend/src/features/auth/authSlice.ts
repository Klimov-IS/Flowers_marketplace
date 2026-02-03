import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { AuthState, User } from '../../types/user';

const initialState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
};

// MVP: Load mock user from localStorage
const savedUser = localStorage.getItem('mock_user');
if (savedUser) {
  try {
    const user = JSON.parse(savedUser);
    initialState.user = user;
    initialState.isAuthenticated = true;
  } catch (e) {
    // Ignore parse errors
  }
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload;
      state.isAuthenticated = true;
      // MVP: Save to localStorage
      localStorage.setItem('mock_user', JSON.stringify(action.payload));
    },
    setToken: (state, action: PayloadAction<string>) => {
      state.token = action.payload;
      localStorage.setItem('auth_token', action.payload);
    },
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      localStorage.removeItem('mock_user');
      localStorage.removeItem('auth_token');
    },
  },
});

export const { setUser, setToken, logout } = authSlice.actions;
export default authSlice.reducer;
