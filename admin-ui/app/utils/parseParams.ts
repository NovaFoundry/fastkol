/**
 * 解析curl命令中的URL和参数
 * @param curlCommand curl命令字符串
 * @returns 包含base_url和params的对象
 */
export function parseCurlCommand(curlCommand: string): { base_url: string, params: Record<string, string> } {
  const params: Record<string, string> = {};
  
  // 提取URL
  const urlMatch = curlCommand.match(/curl\s+'([^']+)'/i);
  if (!urlMatch) {
    throw new Error('未找到有效的URL');
  }
  
  const fullUrl = urlMatch[1];
  
  // 获取不带参数的base_url
  const base_url = fullUrl.split('?')[0];
  
  // 解析URL中的查询参数
  const queryString = fullUrl.split('?')[1];
  if (queryString) {
    const paramPairs = queryString.split('&');
    for (const pair of paramPairs) {
      const [key, value] = pair.split('=');
      if (key && value) {
        params[key] = decodeURIComponent(value);
      }
    }
  }
  
  return { base_url, params };
}