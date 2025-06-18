import axios from 'axios';

// 使用代理路径
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '';

export interface TiktokAccount {
  id: string;
  username: string;
  email: string;
  phone?: string;
  password: string;
  headers?: {
    'x-ladon'?: string;
    'x-khronos'?: string;
    'x-argus'?: string;
    'x-gorgon'?: string;
    cookie?: string;
    [key: string]: string | undefined;
  };
  params?: {
    url?: string;
    [key: string]: string | undefined;
  };
  status: 'normal' | 'login_expired' | 'disabled' | 'deprecated';
}

export interface ListAccountsResponse {
  accounts: TiktokAccount[];
  total: number;
}

export interface CreateAccountRequest {
  username: string;
  email: string;
  phone?: string;
  password: string;
  headers?: {
    'x-ladon'?: string;
    'x-khronos'?: string;
    'x-argus'?: string;
    'x-gorgon'?: string;
    cookie?: string;
    [key: string]: string | undefined;
  };
  params?: {
    url?: string;
    [key: string]: string | undefined;
  };
  status?: string;
}

export interface UpdateAccountRequest extends CreateAccountRequest {
  id: string;
}

const api = {
  // 获取账号列表
  listAccounts: async (
    pageSize: number = 10, 
    pageNum: number = 1, 
    status?: string, 
    username?: string, 
    id?: string, 
    email?: string,
    sortField?: string,
    sortOrder?: 'asc' | 'desc' | null
  ) => {
    const response = await axios.get<ListAccountsResponse>(`${API_BASE_URL}/v1/tiktok/accounts`, {
      params: { pageSize, pageNum, status, username, id, email, sortField, sortOrder }
    });
    return response.data;
  },

  // 获取单个账号
  getAccount: async (id: string) => {
    const response = await axios.get<{ account: TiktokAccount }>(`${API_BASE_URL}/v1/tiktok/accounts/${id}`);
    return response.data.account;
  },

  // 创建账号
  createAccount: async (data: CreateAccountRequest) => {
    const response = await axios.post<{ account: TiktokAccount }>(`${API_BASE_URL}/v1/tiktok/accounts`, data);
    return response.data.account;
  },

  // 更新账号
  updateAccount: async (id: string, data: CreateAccountRequest) => {
    const response = await axios.put<{ account: TiktokAccount }>(`${API_BASE_URL}/v1/tiktok/accounts/${id}`, data);
    return response.data.account;
  },

  // 删除账号
  deleteAccount: async (id: string) => {
    const response = await axios.delete<{ success: boolean }>(`${API_BASE_URL}/v1/tiktok/accounts/${id}`);
    return response.data.success;
  }
};

export default api;