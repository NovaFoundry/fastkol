export interface TaskResponse {
  task_id: string;
}

export interface TaskStatusResponse {
  status: string;
  results?: any[];
}

const API_HOST = process.env.NEXT_PUBLIC_API_HOST || 'http://localhost:10081';

export async function fetchTask(
  path: string,
  params: Record<string, any>
): Promise<TaskResponse> {
  const url = `${API_HOST}${path}`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!response.ok) throw new Error('Failed to fetch');
  return response.json();
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const url = `${API_HOST}/task/${taskId}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to get task status');
  return response.json();
} 