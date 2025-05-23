import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/twitterAccount');
  return null;
} 