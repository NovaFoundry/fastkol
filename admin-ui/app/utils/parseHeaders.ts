export function parseCurlCommand(curlCommand: string): { headers: Record<string, string>, hasCookie: boolean } {
  const headers: Record<string, string> = {};
  const headerRegex = /-H\s+'([^']+)'|--header\s+'([^']+)'/g;
  let match;
  while ((match = headerRegex.exec(curlCommand)) !== null) {
    const headerString = match[1] || match[2];
    const firstColonIndex = headerString.indexOf(':');
    if (firstColonIndex !== -1) {
      const key = headerString.substring(0, firstColonIndex).trim().toLowerCase();
      const value = headerString.substring(firstColonIndex + 1).trim();
      if (key && value) {
        headers[key] = value;
      }
    }
  }
  
  // 检查是否已经从header中解析到cookie
  let hasCookie = Object.keys(headers).some(k => k === 'cookie');
  
  // 如果没有从header中解析到cookie，尝试解析--cookie参数
  if (!hasCookie) {
    const cookieRegex = /--cookie\s+'([^']+)'/g;
    let cookieMatch;
    while ((cookieMatch = cookieRegex.exec(curlCommand)) !== null) {
      const cookieValue = cookieMatch[1];
      if (cookieValue) {
        headers['cookie'] = cookieValue;
        hasCookie = true;
        break;
      }
    }
  }
  
  return { headers, hasCookie };
}

export function parseFirefoxHeaders(headersString: string): { headers: Record<string, string>, hasCookie: boolean } {
  const headers: Record<string, string> = {};
  const lines = headersString.split('\n');
  for (const line of lines) {
    const [key, ...valueParts] = line.split(':');
    if (key && valueParts.length > 0) {
      const value = valueParts.join(':').trim();
      headers[key.trim().toLowerCase()] = value;
    }
  }
  const hasCookie = Object.keys(headers).some(k => k === 'cookie');
  return { headers, hasCookie };
}

export function parseFetchHeaders(fetchString: string): { headers: Record<string, string>, hasCookie: boolean } {
  const match = fetchString.match(/fetch\([^,]+,\s*({[\s\S]*?})\);?$/);
  if (!match) {
    throw new Error('未找到 fetch 参数');
  }
  const options = JSON.parse(match[1]);
  if (!options.headers) {
    throw new Error('未找到 headers 对象');
  }
  const headers: Record<string, string> = {};
  for (const k in options.headers) {
    if (Object.prototype.hasOwnProperty.call(options.headers, k)) {
      headers[k.toLowerCase()] = options.headers[k];
    }
  }
  const hasCookie = Object.keys(headers).some(k => k === 'cookie');
  return { headers, hasCookie };
}