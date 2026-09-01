import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'
const geist = Geist({subsets:['latin'],variable:'--font-geist'})
const mono = Geist_Mono({subsets:['latin'],variable:'--font-mono'})
export const metadata: Metadata = {title:'Nirikshan — MPLADS Oversight Console',description:'Explainable anomaly screening for public infrastructure projects.',generator:'v0.app'}
export const viewport: Viewport = {colorScheme:'light dark',themeColor:[{media:'(prefers-color-scheme: light)',color:'#f5f7f5'},{media:'(prefers-color-scheme: dark)',color:'#17201f'}]}
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en" className="bg-background"><body className={`${geist.variable} ${mono.variable} antialiased`}>{children}</body></html>}
