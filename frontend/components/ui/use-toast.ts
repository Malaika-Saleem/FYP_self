import { useEffect, useState } from 'react'

type ToastProps = {
  title: string
  description?: string
  variant?: 'default' | 'destructive'
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastProps[]>([])

  const toast = ({ title, description, variant = 'default' }: ToastProps) => {
    // For now, use console.log. In production, this would trigger a toast notification
    console.log(`Toast [${variant}]: ${title}${description ? ` - ${description}` : ''}`)
    
    // You can integrate with a proper toast library like sonner or react-hot-toast
    setToasts(prev => [...prev, { title, description, variant }])
  }

  return { toast, toasts }
}
