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

export default function SearchPage() {
  const [platform, setPlatform] = useState('');
  const [query, setQuery] = useState('');
  const [taskId, setTaskId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState('');
  const [results, setResults] = useState<any>(null);
  const [form] = Form.useForm();

  const handleSubmit = async (values: any) => {
    setIsLoading(true);
    try {
      const response = await fetchTask('/fetch/search', {
        platform: values.platform,
        query: values.query,
        count: values.count || 100,
        follows: {
          min: 100,
          max: 1000
        }
      });
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
    const filename = `search_${platform}_${query}_${timestamp}.xlsx`;
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
              <Title level={2} className="mb-2">Search Accounts</Title>
              <Text type="secondary">Search for accounts across different social media platforms</Text>
            </div>

            <Form
              form={form}
              onFinish={handleSubmit}
              layout="vertical"
              requiredMark={false}
              initialValues={{ count: 100 }}
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
                  <Option value="tiktok">TikTok</Option>
                  <Option value="youtube">YouTube</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="query"
                label="Query"
                rules={[{ required: true, message: 'Please enter query' }]}
              >
                <Input
                  size="large"
                  placeholder="Enter query"
                  onChange={(e) => setQuery(e.target.value)}
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

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  size="large"
                  icon={<SearchOutlined />}
                  loading={isLoading}
                  block
                >
                  Search Accounts
                </Button>
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