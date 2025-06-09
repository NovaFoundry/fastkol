'use client';

import React, { useState } from 'react';
import { fetchTask, getTaskStatus } from '../../lib/api';
import * as XLSX from 'xlsx';
import { 
  Card, 
  Form, 
  Select, 
  Input, 
  Button, 
  Space, 
  Typography, 
  Alert, 
  Spin,
  message,
  Progress,
  InputNumber
} from 'antd';
import { 
  SearchOutlined, 
  DownloadOutlined, 
  CheckCircleOutlined, 
  LoadingOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Option } = Select;

export default function SimilarPage() {
  const [platform, setPlatform] = useState('');
  const [username, setUsername] = useState('');
  const [taskId, setTaskId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [results, setResults] = useState<any>(null);
  const [form] = Form.useForm();

  const handleSubmit = async (values: any) => {
    // 校验最大值大于最小值
    if (
      values.followsMin !== undefined && values.followsMin !== '' &&
      values.followsMax !== undefined && values.followsMax !== '' &&
      Number(values.followsMax) <= Number(values.followsMin)
    ) {
      message.error('最大值必须大于最小值');
      return;
    }
    setIsLoading(true);
    try {
      const follows: any = {};
      if (values.followsMin !== undefined && values.followsMin !== '') follows.min = values.followsMin;
      if (values.followsMax !== undefined && values.followsMax !== '') follows.max = values.followsMax;
      const payload: any = {
        platform: values.platform,
        username: values.username,
        count: values.count || 50
      };
      if (Object.keys(follows).length > 0) payload.follows = follows;
      const response = await fetchTask('/fetch/similar', payload);
      setTaskId(response.task_id);
      setStatus('pending');
      message.success('Task created successfully!');
      pollTaskStatus(response.task_id);
    } catch (error) {
      console.error('Error:', error);
      message.error('Failed to create task');
    }
    setIsLoading(false);
  };

  const pollTaskStatus = async (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await getTaskStatus(taskId);
        setStatus(response.status);
        if (response.status === 'completed') {
          setResults(response.results);
          message.success('Task completed!');
          clearInterval(interval);
        } else if (response.status === 'failed') {
          message.error('Task failed!');
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Error polling status:', error);
        message.error('Failed to get task status');
        clearInterval(interval);
      }
    }, 10000);
  };

  const downloadExcel = () => {
    if (!results) return;
    const now = new Date();
    const timestamp = now.toISOString().replace(/[:.]/g, '-');
    const filename = `similar_${platform}_${username}_${timestamp}.xlsx`;
    const worksheet = XLSX.utils.json_to_sheet(results);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Results');
    XLSX.writeFile(workbook, filename);
    message.success('Excel file downloaded successfully!');
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      default:
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-3xl mx-auto">
        <Card className="mb-6 shadow-md">
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Title level={2} className="mb-2">Similar Accounts Fetcher</Title>
              <Text type="secondary">Find similar accounts across different social media platforms</Text>
            </div>

            <Form
              form={form}
              onFinish={handleSubmit}
              layout="vertical"
              requiredMark={false}
              initialValues={{ count: 50, followsMin: 10000 }}
            >
              <Form.Item
                name="platform"
                label="Platform"
                rules={[{ required: true, message: 'Please select a platform' }]}
              >
                <Select
                  placeholder="Select platform"
                  size="large"
                  onChange={(value) => setPlatform(value)}
                >
                  <Option value="twitter">Twitter</Option>
                  <Option value="instagram">Instagram</Option>
                  {/* <Option value="tiktok">TikTok</Option>
                  <Option value="youtube">YouTube</Option> */}
                </Select>
              </Form.Item>

              <Form.Item
                name="username"
                label="Username"
                rules={[{ required: true, message: 'Please enter username' }]}
              >
                <Input
                  size="large"
                  placeholder="Enter username"
                  onChange={(e) => setUsername(e.target.value)}
                />
              </Form.Item>

              <Form.Item
                name="count"
                label="Count"
                rules={[
                  { required: true, message: 'Please enter count' },
                  { type: 'number', min: 1, max: 200, message: 'Count must be between 1 and 200' }
                ]}
              >
                <InputNumber
                  size="large"
                  style={{ width: '100%' }}
                  placeholder="Enter count"
                  min={1}
                  max={200}
                />
              </Form.Item>

              <Form.Item label="Follows" style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Form.Item
                    name="followsMin"
                    noStyle
                    initialValue={10000}
                  >
                    <InputNumber
                      size="large"
                      style={{ flex: 1, width: '100%' }}
                      placeholder="最小值"
                      min={0}
                    />
                  </Form.Item>
                  <span style={{ margin: '0 8px', whiteSpace: 'nowrap' }}>-</span>
                  <Form.Item
                    name="followsMax"
                    noStyle
                  >
                    <InputNumber
                      size="large"
                      style={{ flex: 1, width: '100%' }}
                      placeholder="∞"
                      min={0}
                      formatter={(value: number | string | undefined) => {
                        if (value === undefined || value === null || value === '') return '∞';
                        return String(value);
                      }}
                      parser={(value: string | undefined) => {
                        if (value === '∞' || value === undefined || value === null || value === '') return '';
                        return value.replace(/[^\d]/g, '');
                      }}
                    />
                  </Form.Item>
                </div>
              </Form.Item>

              <Form.Item>
                <div style={{ marginTop: 24 }}>
                  <Button
                    type="primary"
                    htmlType="submit"
                    size="large"
                    icon={<SearchOutlined />}
                    loading={isLoading}
                    block
                  >
                    Find Similar Accounts
                  </Button>
                </div>
              </Form.Item>
            </Form>
          </Space>
        </Card>

        {taskId && (
          <Card className="shadow-md">
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Alert
                message="Task Status"
                description={
                  <Space direction="vertical" size="small">
                    <Text>Task ID: <Text code>{taskId}</Text></Text>
                    <Space>
                      {getStatusIcon()}
                      <Text>Status: <Text strong>{status}</Text></Text>
                    </Space>
                  </Space>
                }
                type={status === 'completed' ? 'success' : 'info'}
                showIcon
              />

              {status === 'pending' && (
                <Progress percent={99} status="active" />
              )}

              {status === 'completed' && results && (
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  onClick={downloadExcel}
                  size="large"
                  block
                >
                  Download Excel
                </Button>
              )}
            </Space>
          </Card>
        )}
      </div>
    </main>
  );
} 