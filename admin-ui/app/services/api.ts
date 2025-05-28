import axios from 'axios';

// 使用代理路径
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '';

export interface TwitterAccount {
  id: string;
  username: string;
  email: string;
  phone?: string;
  password: string;
  headers?: {
    authorization?: string;
    'x-csrf-token'?: string;
    'x-client-transaction-id'?: string;
    cookie?: string;
    [key: string]: string | undefined;
  };
  status: 'normal' | 'login_expired' | 'disabled' | 'deprecated' | 'suspended';
}

export interface ListAccountsResponse {
  accounts: TwitterAccount[];
  total: number;
}

export interface CreateAccountRequest {
  username: string;
  email: string;
  phone?: string;
  password: string;
  headers?: {
    authorization?: string;
    'x-csrf-token'?: string;
    'x-client-transaction-id'?: string;
    cookie?: string;
    [key: string]: string | undefined;
  };
  status?: string;
}

export interface UpdateAccountRequest extends CreateAccountRequest {
  id: string;
}

const api = {
  // 获取账号列表
  listAccounts: async (pageSize: number = 10, pageNum: number = 1, status?: string) => {
    const response = await axios.get<ListAccountsResponse>(`${API_BASE_URL}/v1/twitter/accounts`, {
      params: { pageSize, pageNum, status }
    });
    return response.data;
  },

  // 获取单个账号
  getAccount: async (id: string) => {
    const response = await axios.get<{ account: TwitterAccount }>(`${API_BASE_URL}/v1/twitter/accounts/${id}`);
    return response.data.account;
  },

  // 创建账号
  createAccount: async (data: CreateAccountRequest) => {
    const response = await axios.post<{ account: TwitterAccount }>(`${API_BASE_URL}/v1/twitter/accounts`, data);
    return response.data.account;
  },

  // 更新账号
  updateAccount: async (id: string, data: CreateAccountRequest) => {
    const response = await axios.put<{ account: TwitterAccount }>(`${API_BASE_URL}/v1/twitter/accounts/${id}`, data);
    return response.data.account;
  },

  // 删除账号
  deleteAccount: async (id: string) => {
    const response = await axios.delete<{ success: boolean }>(`${API_BASE_URL}/v1/twitter/accounts/${id}`);
    return response.data.success;
  }
};

export default api; 