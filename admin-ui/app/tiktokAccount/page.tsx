'use client';

import { useState, useEffect } from 'react';
import { Table, Button, Space, Modal, Form, Input, Select, message, Popconfirm, Collapse, App, Alert } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { SortOrder } from 'antd/es/table/interface';
import api, { TiktokAccount, CreateAccountRequest } from '../services/tiktokApi';
import { parseCurlCommand as parseHeaders } from '../utils/parseHeaders';
import { parseCurlCommand as parseParams } from '../utils/parseParams';

const { Option } = Select;
const { Panel } = Collapse;

export default function Home() {
  const [accounts, setAccounts] = useState<TiktokAccount[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingAccount, setEditingAccount] = useState<TiktokAccount | null>(null);
  const [form] = Form.useForm();
  const [curlInput, setCurlInput] = useState('');
  const [allVisible, setAllVisible] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchModalVisible, setBatchModalVisible] = useState(false);
  const [batchStatus, setBatchStatus] = useState<string>('normal');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [sortField, setSortField] = useState<string | undefined>(undefined);
  const [sortOrder, setSortOrder] = useState<SortOrder>(null);

  const statusMap: Record<TiktokAccount['status'], string> = {
    normal: '正常',
    login_expired: '登录已失效',
    disabled: '已禁用',
    deprecated: '已废弃',
  };

  const statusColor: Record<TiktokAccount['status'], string> = {
    normal: '#52c41a',
    login_expired: '#ff4d4f',
    disabled: '#bfbfbf',
    deprecated: '#faad14',
  };

  const getSearchParams = (keyword: string) => {
    if (!keyword) return { username: undefined, id: undefined, email: undefined };
    
    // 判断是否为邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (emailRegex.test(keyword)) {
      return { username: undefined, id: undefined, email: keyword };
    }
    
    // 判断是否为ID格式（假设ID是纯数字）
    const idRegex = /^\d+$/;
    if (idRegex.test(keyword)) {
      return { username: undefined, id: keyword, email: undefined };
    }
    
    // 默认为用户名搜索
    return { username: keyword, id: undefined, email: undefined };
  };

  const fetchAccounts = async (page = 1, pageSize = 10, status = statusFilter) => {
    try {
      setLoading(true);
      const { username, id, email } = getSearchParams(searchKeyword);
      const response = await api.listAccounts(
        pageSize, 
        page, 
        status && status !== 'all' ? status : undefined,
        username,
        id,
        email,
        sortField,
        sortOrder === 'ascend' ? 'asc' : sortOrder === 'descend' ? 'desc' : null
      );
      setAccounts(response.accounts);
      setTotal(response.total);
    } catch (error) {
      message.error('获取账号列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, [statusFilter, searchKeyword, sortField, sortOrder]);

  const handleCreate = () => {
    setEditingAccount(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: TiktokAccount) => {
    setEditingAccount(record);
    form.setFieldsValue({
      ...record,
      headers: record.headers ? JSON.stringify(record.headers, null, 2) : '',
      params: record.params ? JSON.stringify(record.params, null, 2) : '',
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteAccount(id);
      message.success('删除成功');
      fetchAccounts();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      let headers = values.headers ? JSON.parse(values.headers) : undefined;
      let params = values.params ? JSON.parse(values.params) : undefined;
      
      if (headers) {
        const lowerCaseHeaders: Record<string, string> = {};
        for (const k in headers) {
          if (Object.prototype.hasOwnProperty.call(headers, k)) {
            lowerCaseHeaders[k.toLowerCase()] = headers[k];
          }
        }
        headers = lowerCaseHeaders;
      }
      
      const data: CreateAccountRequest = {
        ...values,
        headers,
        params,
      };

      if (editingAccount) {
        await api.updateAccount(editingAccount.id, data);
        message.success('更新成功');
      } else {
        await api.createAccount(data);
        message.success('创建成功');
      }

      setModalVisible(false);
      setCurlInput('');
      fetchAccounts();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleCurlParse = () => {
    try {
      // 解析Headers
      const { headers, hasCookie } = parseHeaders(curlInput);
      form.setFieldValue('headers', JSON.stringify(headers, null, 2));
      
      // 检查必要的Header字段
      const requiredHeaders = ['x-ladon', 'x-khronos', 'x-argus', 'x-gorgon', 'cookie'];
      const missingHeaders = requiredHeaders.filter(h => !headers[h]);
      
      if (missingHeaders.length > 0) {
        message.warning(`未检测到以下字段: ${missingHeaders.join(', ')}`);
      } else {
        message.success('Headers 解析成功');
      }
      
      // 解析URL和参数
      const { base_url, params } = parseParams(curlInput);
      if (base_url) {
        // 将base_url也添加到params中
        params.base_url = base_url;
        form.setFieldValue('params', JSON.stringify(params, null, 2));
        message.success('URL和参数解析成功');
      }
    } catch (error) {
      message.error('Curl 命令解析失败');
    }
  };

  const handleToggleAllPasswords = () => {
    if (allVisible) {
      setAllVisible(false);
    } else {
      setAllVisible(true);
    }
  };

  const handleBatchStatusChange = async () => {
    try {
      await Promise.all(selectedRowKeys.map(id => {
        const account = accounts.find(acc => acc.id === id);
        if (!account) return Promise.resolve();
        return api.updateAccount(id as string, {
          username: account.username,
          email: account.email,
          phone: account.phone,
          password: account.password,
          headers: account.headers,
          params: account.params,
          status: batchStatus,
        });
      }));
      message.success('批量修改成功');
      setBatchModalVisible(false);
      setSelectedRowKeys([]);
      fetchAccounts();
    } catch (error) {
      message.error('批量修改失败');
    }
  };

  const columns: ColumnsType<TiktokAccount> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      sorter: true,
      sortOrder: sortField === 'id' ? sortOrder : null,
      onHeaderCell: () => ({
        onClick: () => {
          if (sortField !== 'id') {
            setSortField('id');
            setSortOrder('ascend');
          } else if (sortOrder === null) {
            setSortOrder('ascend');
          } else if (sortOrder === 'ascend') {
            setSortOrder('descend');
          } else {
            setSortField(undefined);
            setSortOrder(null);
          }
        }
      })
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '手机号',
      dataIndex: 'phone',
      key: 'phone',
    },
    {
      title: (
        <span>
          密码
          <Button
            type="link"
            size="small"
            icon={allVisible ? <EyeInvisibleOutlined /> : <EyeOutlined />}
            onClick={handleToggleAllPasswords}
            style={{ marginLeft: 4, padding: 0, height: 'auto', verticalAlign: 'middle' }}
            tabIndex={-1}
          />
        </span>
      ),
      dataIndex: 'password',
      key: 'password',
      width: 160,
      render: (password: string) => (
        <span
          style={{
            fontFamily: 'monospace',
            minWidth: 160,
            width: 160,
            display: 'inline-block',
          }}
          title={allVisible ? password : undefined}
        >
          {allVisible ? password : '*'.repeat(16)}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: TiktokAccount['status']) => {
        return <span style={{ color: statusColor[status] }}>{statusMap[status] || status}</span>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个账号吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <App>
      <div className="p-6">
        <div className="mb-4" style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            新建账号
          </Button>
          <Input.Search
            placeholder="搜索用户名/ID/邮箱"
            allowClear
            style={{ width: 250 }}
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            onSearch={() => fetchAccounts()}
          />
          <Select
            value={statusFilter || 'all'}
            style={{ width: 160 }}
            onChange={value => setStatusFilter(value)}
            options={[
              { value: 'all', label: '全部' },
              { value: 'normal', label: <><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: '#52c41a', marginRight: 8, verticalAlign: 'middle' }}></span>正常</> },
              { value: 'login_expired', label: <><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ff4d4f', marginRight: 8, verticalAlign: 'middle' }}></span>登录已失效</> },
              { value: 'disabled', label: <><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: '#bfbfbf', marginRight: 8, verticalAlign: 'middle' }}></span>已禁用</> },
              { value: 'deprecated', label: <><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: '#faad14', marginRight: 8, verticalAlign: 'middle' }}></span>已废弃</> },
            ]}
          />
          <Button
            disabled={selectedRowKeys.length === 0}
            onClick={() => setBatchModalVisible(true)}
          >
            批量修改状态
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={accounts}
          rowKey="id"
          loading={loading}
          pagination={{
            total,
            onChange: (page, pageSize) => fetchAccounts(page, pageSize),
          }}
          rowSelection={{
            selectedRowKeys,
            onChange: setSelectedRowKeys,
          }}
        />

        <Modal
          title={editingAccount ? '编辑账号' : '新建账号'}
          open={modalVisible}
          onOk={handleSubmit}
          onCancel={() => {
            setModalVisible(false);
            setCurlInput('');
          }}
          width={800}
        >
          <Form
            form={form}
            layout="vertical"
            initialValues={{ status: 'normal' }}
          >
            <Form.Item
              name="username"
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input />
            </Form.Item>

            <Form.Item
              name="email"
              label="邮箱"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
            >
              <Input />
            </Form.Item>

            <Form.Item
              name="phone"
              label="手机号"
            >
              <Input />
            </Form.Item>

            <Form.Item
              name="password"
              label="密码"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password />
            </Form.Item>

            <Form.Item
              name="status"
              label="状态"
              rules={[{ required: true, message: '请选择状态' }]}
            >
              <Select>
                <Option value="normal"><span style={{ color: statusColor['normal'] }}>正常</span></Option>
                <Option value="login_expired"><span style={{ color: statusColor['login_expired'] }}>登录已失效</span></Option>
                <Option value="disabled"><span style={{ color: statusColor['disabled'] }}>已禁用</span></Option>
                <Option value="deprecated"><span style={{ color: statusColor['deprecated'] }}>已废弃</span></Option>
              </Select>
            </Form.Item>

            <Alert
              message="💡 提示"
              description="请从TikTok API请求中复制curl命令，解析后会自动填充Headers和Params"
              type="info"
              showIcon
              className="mb-4"
            />

            <Collapse 
              className="mb-4"
              items={[
                {
                  key: '1',
                  label: '从 Curl 命令导入 Headers 和 Params',
                  children: (
                    <>
                      <Input.TextArea
                        value={curlInput}
                        onChange={(e) => setCurlInput(e.target.value)}
                        placeholder="请粘贴使用单引号的 curl 命令，例如：curl 'https://example.com' -H 'Cookie: key=value'"
                        rows={4}
                      />
                      <div className="text-gray-500 text-sm mt-1 mb-2">
                        <div>⚠️ 注意事项：</div>
                        <div>1. 仅支持使用单引号的 curl 命令</div>
                        <div>2. 支持的格式：</div>
                        <div className="ml-4">-H 'X-Ladon: value'</div>
                        <div className="ml-4">-H 'X-Khronos: value'</div>
                        <div className="ml-4">-H 'X-Argus: value'</div>
                        <div className="ml-4">-H 'X-Gorgon: value'</div>
                        <div className="ml-4">-H 'Cookie: value'</div>
                      </div>
                      <Button
                        type="primary"
                        onClick={handleCurlParse}
                        className="mt-2"
                      >
                        解析 Curl 命令
                      </Button>
                    </>
                  )
                }
              ]}
            />

            <Form.Item
              name="headers"
              label="Headers"
              rules={[
                {
                  validator: async (_, value) => {
                    if (value) {
                      try {
                        JSON.parse(value);
                      } catch (e) {
                        throw new Error('请输入有效的 JSON 格式');
                      }
                    }
                  },
                },
              ]}
            >
              <Input.TextArea rows={6} />
            </Form.Item>

            <Form.Item
              name="params"
              label="Params"
              rules={[
                {
                  validator: async (_, value) => {
                    if (value) {
                      try {
                        JSON.parse(value);
                      } catch (e) {
                        throw new Error('请输入有效的 JSON 格式');
                      }
                    }
                  },
                },
              ]}
            >
              <Input.TextArea rows={6} />
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title="批量修改状态"
          open={batchModalVisible}
          onOk={handleBatchStatusChange}
          onCancel={() => setBatchModalVisible(false)}
        >
          <Select
            value={batchStatus}
            style={{ width: 200 }}
            onChange={setBatchStatus}
            options={[
              { value: 'normal', label: <><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: '#52c41a', marginRight: 8, verticalAlign: 'middle' }}></span>正常</> },
              { value: 'login_expired', label: <><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: '#ff4d4f', marginRight: 8, verticalAlign: 'middle' }}></span>登录已失效</> },
              { value: 'disabled', label: <><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: '#bfbfbf', marginRight: 8, verticalAlign: 'middle' }}></span>已禁用</> },
              { value: 'deprecated', label: <><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: '#faad14', marginRight: 8, verticalAlign: 'middle' }}></span>已废弃</> },
            ]}
          />
        </Modal>
      </div>
    </App>
  );
}