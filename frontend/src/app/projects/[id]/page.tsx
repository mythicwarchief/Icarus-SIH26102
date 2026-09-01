import { Investigation } from '@/components/Dashboard'
import { getProject, projects } from '@/lib/types'
export function generateStaticParams(){return projects.map(p=>({id:p.id}))}
export default async function ProjectPage({params}:{params:Promise<{id:string}>}){const {id}=await params; return <Investigation project={getProject(id)} />}
