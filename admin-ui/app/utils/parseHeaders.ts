export function parseCurlCommand(curlCommand: string): { headers: Record<string, string>, hasCookie: boolean } {
  const headers: Record<string, string> = {};
  const headerRegex = /-H\s+'([^']+)'|--header\s+'([^']+)'/g;
  let match;
  while ((match = headerRegex.exec(curlCommand)) !== null) {
    const headerString = match[1] || match[2];
    const firstColonIndex = headerString.indexOf(':');
    if (firstColonIndex !== -1) {
      const key = headerString.substring(0, firstColonIndex).trim();
      const value = headerString.substring(firstColonIndex + 1).trim();
      if (key && value) {
        headers[key] = value;
      }
    }
  }
  const hasCookie = Object.keys(headers).some(k => k.toLowerCase() === 'cookie');
  return { headers, hasCookie };
}

export function parseFirefoxHeaders(headersString: string): { headers: Record<string, string>, hasCookie: boolean } {
  const headers: Record<string, string> = {};
  const lines = headersString.split('\n');
  for (const line of lines) {
    const [key, ...valueParts] = line.split(':');
    if (key && valueParts.length > 0) {
      const value = valueParts.join(':').trim();
      headers[key.trim()] = value;
    }
  }
  const hasCookie = Object.keys(headers).some(k => k.toLowerCase() === 'cookie');
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
  const headers = options.headers;
  const hasCookie = Object.keys(headers).some(k => k.toLowerCase() === 'cookie');
  return { headers, hasCookie };
} 