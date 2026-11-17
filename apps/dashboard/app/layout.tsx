import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Zyntrava Shield · Local console', description: 'Authenticated local security research console.', robots: { index: false, follow: false } };
export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
