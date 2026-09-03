import { InvestigationWithLoading } from '@/components/Dashboard'

export default async function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <InvestigationWithLoading workId={id} />
}