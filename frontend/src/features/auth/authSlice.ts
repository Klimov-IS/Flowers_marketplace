import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { User } from '../../types/user';

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// Initialize from localStorage
const loadAuthState = (): Partial<AuthState> => {
  try {
    const accessToken = localStorage.getItem('access_token');
    const refreshToken = localStorage.getItem('refresh_token');
    const savedUser = localStorage.getItem('user');

    if (accessToken && savedUser) {
      return {
        accessToken,
        refreshToken,
        user: JSON.parse(savedUser),
        isAuthenticated: true,
      };
    }
  } catch (e) {
    // Clear corrupted data
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  }
  return {};
};

const savedState = loadAuthState();

const initialState: AuthState = {
  user: savedState.user || null,
  accessToken: savedState.accessToken || null,
  refreshToken: savedState.refreshToken || null,
  isAuthenticated: savedState.isAuthenticated || false,
  isLoading: false,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (
      state,
      action: PayloadAction<{
        user: User;
        accessToken: string;
        refreshToken: string;
      }>
    ) => {
      state.user = action.payload.user;
      state.accessToken = action.payload.accessToken;
      state.refreshToken = action.payload.refreshToken;
      state.isAuthenticated = true;
      state.isLoading = false;

      // Persist to localStorage
      localStorage.setItem('access_token', action.payload.accessToken);
      localStorage.setItem('refresh_token', action.payload.refreshToken);
      localStorage.setItem('user', JSON.stringify(action.payload.user));
    },

    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload;
      state.isAuthenticated = true;
      localStorage.setItem('user', JSON.stringify(action.payload));
    },

    setTokens: (
      state,
      action: PayloadAction<{ accessToken: string; refreshToken: string }>
    ) => {
      state.accessToken = action.payload.accessToken;
      state.refreshToken = action.payload.refreshToken;
      localStorage.setItem('access_token', action.payload.accessToken);
      localStorage.setItem('refresh_token', action.payload.refreshToken);
    },

    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },

    logout: (state) => {
      state.user = null;
      state.accessToken = null;
      state.refreshToken = null;
      state.isAuthenticated = false;
      state.isLoading = false;

      // Clear localStorage
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      // Clean up old keys
      localStorage.removeItem('mock_user');
      localStorage.removeItem('auth_token');
    },
  },
});

export const { setCredentials, setUser, setTokens, setLoading, logout } =
  authSlice.actions;
export default authSlice.reducer;
