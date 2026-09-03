import { InvestigationWithLoading } from '@/components/Dashboard'

export default async function ProjectPage({ params }: { params: Promise<{ id: string[] }> }) {
  const { id } = await params
  const workId = decodeURIComponent(id.join('/'))
  return <InvestigationWithLoading workId={workId} />
}