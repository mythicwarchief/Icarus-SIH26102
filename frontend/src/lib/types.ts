export type ProjectStatus = 'not_started' | 'ongoing' | 'completed'
export type RiskTier = 'low' | 'medium' | 'high'
export type AnomalyType = 'cost_overrun' | 'delay' | 'duplicate' | 'payment_irregularity' | 'geospatial_mismatch'

export interface Anomaly { type: AnomalyType; confidence: number; explanation: string }
export interface Project {
  id: string; name: string; location: string; region: string; status: ProjectStatus
  sanctionedAmount: number; releasedAmount: number; utilizedAmount: number
  plannedDuration: number; actualDuration: number | null; sanctionedDate: string
  workStartDate: string | null; completedDate: string | null; riskScore: number; riskTier: RiskTier
  isFlagged: boolean; flaggedDate: string | null; anomalies?: Anomaly[]
  duplicateMatch?: { matchedProjectId: string; matchedProjectName: string; similarityScore: number; reason: string }
  verificationStatus?: 'unverified' | 'verified_clean' | 'escalated'
}
export interface DashboardSummary { totalProjects:number; totalSanctionedValue:number; flaggedCount:number; highPriorityCount:number; duplicateMatchCount:number; cleanCount:number }
export const anomalyLabels: Record<AnomalyType,string> = { cost_overrun:'Cost variance', delay:'Delay pattern', duplicate:'Duplicate work', payment_irregularity:'Payment irregularity', geospatial_mismatch:'Location mismatch' }
export const formatINR = (value:number) => value >= 10000000 ? `₹${(value/10000000).toFixed(1)} Cr` : `₹${(value/100000).toFixed(1)} L`
export const statusLabels: Record<ProjectStatus,string> = { not_started:'Not started', ongoing:'Ongoing', completed:'Completed' }
export const riskClass = (tier:RiskTier) => tier === 'high' ? 'risk-high' : tier === 'medium' ? 'risk-medium' : 'risk-low'

const names = ['Rural Road Connectivity','Community Health Centre','Drinking Water Network','Solar Street Lighting','Government School Upgrade','Irrigation Canal Repair','Multi-purpose Community Hall','District Library Digital Hub']
const places = [['Kangra','Himachal Pradesh'],['Gaya','Bihar'],['Mysuru','Karnataka'],['Barpeta','Assam'],['Nashik','Maharashtra'],['Kollam','Kerala'],['Jabalpur','Madhya Pradesh'],['Cuttack','Odisha']]
export const projects: Project[] = Array.from({length:72},(_,i) => {
  const flagged = i % 4 === 0 || i % 11 === 0, high = i % 9 === 0 || i % 17 === 0
  const riskScore = high ? 78 + (i%18) : flagged ? 42 + (i%27) : 8 + (i%29)
  const [city,region] = places[i%places.length]; const sanctioned = 2800000 + (i%13)*1750000
  const status: ProjectStatus = i%7===0 ? 'not_started' : i%3===0 ? 'completed' : 'ongoing'
  const anomalies: Anomaly[] = flagged ? [{type: i%3===0?'cost_overrun':'delay', confidence: .72+(i%3)/10, explanation: i%3===0 ? 'Utilization is 18% above the median for comparable works in this region.' : 'Current milestone is 64 days behind the planned completion window.'}] : []
  if (i%11===0) anomalies.push({type:'duplicate',confidence:.91,explanation:'Project description and coordinates closely match another sanctioned work nearby.'})
  return {id:`MPLADS-${String(26102+i).padStart(5,'0')}`,name:`${names[i%names.length]} — ${city}`,location:city,region,status,sanctionedAmount:sanctioned,releasedAmount:sanctioned*(.55+(i%4)/10),utilizedAmount:sanctioned*(.35+(i%6)/10),plannedDuration:180+(i%5)*30,actualDuration:status==='completed'?210+(i%7)*22:null,sanctionedDate:`202${i%4+2}-0${i%8+1}-12`,workStartDate:status==='not_started'?null:`202${i%4+2}-0${i%8+1}-28`,completedDate:status==='completed'?`202${i%4+3}-0${i%8+1}-18`:null,riskScore,riskTier:high?'high':flagged?'medium':'low',isFlagged:flagged,flaggedDate:flagged?'2026-08-2'+(i%8):null,anomalies,duplicateMatch:i%11===0?{matchedProjectId:`MPLADS-${26102+i-3}`,matchedProjectName:`${names[(i+2)%names.length]} — ${city}`,similarityScore:91,reason:'Near-identical scope and spatial proximity within 2.4 km.'}:undefined,verificationStatus:flagged?'unverified':'verified_clean'}
})
export const getSummary = (): DashboardSummary => ({totalProjects:projects.length,totalSanctionedValue:projects.reduce((a,p)=>a+p.sanctionedAmount,0),flaggedCount:projects.filter(p=>p.isFlagged).length,highPriorityCount:projects.filter(p=>p.riskTier==='high').length,duplicateMatchCount:projects.filter(p=>p.duplicateMatch).length,cleanCount:projects.filter(p=>!p.isFlagged).length})
export const getProject = (id:string) => projects.find(p=>p.id===id) ?? projects[0]
export const riskDistribution = [{name:'Low risk',value:projects.filter(p=>p.riskTier==='low').length,fill:'#2f8f83'},{name:'Medium risk',value:projects.filter(p=>p.riskTier==='medium').length,fill:'#d89b3d'},{name:'High risk',value:projects.filter(p=>p.riskTier==='high').length,fill:'#c95c4b'}]
export const anomalyBreakdown = Object.entries(anomalyLabels).map(([key,name])=>({name,value:projects.filter(p=>p.anomalies?.some(a=>a.type===key)).length})).filter(x=>x.value)
export const monthlyTrend = ['Mar','Apr','May','Jun','Jul','Aug'].map((month,i)=>({month,flagged:8+i*3,reviewed:18+i*5,expenditure:42+i*7}))
export const regionalRisk = places.slice(0,6).map(([region],i)=>({region,risk:38+i*6,projects:8+i*2}))
