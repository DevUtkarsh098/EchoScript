import { useEffect, useMemo, useRef, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Bell, BookOpen, Bot, Check, CheckCircle2, ChevronRight, CircleAlert, Clock3, CloudUpload,
  Copy, Download, FileAudio, FileText, Film, FolderOpen, Gauge, Grid2X2, Headphones, Home, Languages,
  List, LoaderCircle, LogOut, Menu, Mic2, Moon, MoreHorizontal, Play, Plus, RefreshCw, Search, Settings,
  Sparkles, UploadCloud, User, Video, WandSparkles, X, Zap
} from 'lucide-react'
import { api, downloadAsset, getAsset, uploadFile } from './api'
import type { Job, JobStatus } from './types'
import { isMockAuthEnabled } from './auth-config'

const mockAuth = isMockAuthEnabled(import.meta.env.VITE_APP_ENV, import.meta.env.VITE_MOCK_AUTH)

function useProtectedAsset(path?: string) {
  const [url, setUrl] = useState<string>()
  useEffect(() => {
    let active = true
    let objectUrl: string | undefined
    setUrl(undefined)
    if (path) {
      getAsset(path).then(blob => {
        if (active) {
          objectUrl = URL.createObjectURL(blob)
          setUrl(objectUrl)
        }
      }).catch(() => { if (active) setUrl(undefined) })
    }
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [path])
  return url
}

function DownloadFileButton({ path, className, title, children }: { path?: string; className: string; title?: string; children: React.ReactNode }) {
  const [error, setError] = useState(false)
  const [busy, setBusy] = useState(false)
  return <>
    <button type="button" className={className} title={title} disabled={!path || busy} onClick={async () => {
      if (!path) return
      setBusy(true)
      setError(false)
      try { await downloadAsset(path, path.split('/').pop() || 'download') }
      catch { setError(true) }
      finally { setBusy(false) }
    }}>{children}</button>
    {error && <span role="alert">Download failed. Please try again.</span>}
  </>
}

function Brand({ compact = false }: { compact?: boolean }) {
  return <div className="brand"><span className="brand-mark"><i /><i /><i /><i /></span>{!compact && <span><b>EchoScript</b><small>STUDIO</small></span>}</div>
}

function StatusPill({ status }: { status: string }) {
  const key = status.toLowerCase()
  const label: Record<string, string> = { transcribed: 'Completed', running: 'Processing', uploaded: 'Ready', created: 'Created', failed: 'Failed', none: 'Not requested', done: 'Ready', pending: 'Pending', rendering: 'Rendering' }
  return <span className={`status ${key}`}><span />{label[key] || status}</span>
}

function Empty({ title, body, action }: { title: string; body: string; action?: React.ReactNode }) {
  return <div className="empty"><div className="empty-icon"><FileAudio /></div><h3>{title}</h3><p>{body}</p>{action}</div>
}

function useJobs() {
  return useQuery({ queryKey: ['jobs'], queryFn: api.jobs, refetchInterval: query => query.state.data?.some(item => item.status === 'RUNNING' || ['PENDING', 'RENDERING'].includes(item.video_status)) ? 3000 : false })
}

function Shell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const links = [{ to: '/dashboard', label: 'Home', icon: Home }, { to: '/studio/transcribe', label: 'Studio', icon: Mic2 }, { to: '/jobs', label: 'My Jobs', icon: Gauge }, { to: '/library', label: 'My Library', icon: FolderOpen }]
  return <div className="app-shell">
    <header className="topbar"><div className="nav-inner"><Brand /><button className="menu-button" onClick={() => setOpen(!open)} aria-label="Toggle navigation"><Menu /></button>
      <nav className={open ? 'open' : ''}>{links.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} onClick={() => setOpen(false)}><Icon />{label}</NavLink>)}</nav>
      <div className="top-actions"><button className="icon-button" title="Notifications"><Bell /><span className="notification-dot" /></button><button className="icon-button" title="Appearance"><Moon /></button><button className="profile-button" onClick={() => navigate('/settings')}><span>AM</span><div><b>Alex Morgan</b><small>Workspace</small></div></button></div>
    </div></header><main>{children}</main>
  </div>
}

function PageHead({ eyebrow, title, subtitle, actions }: { eyebrow?: string; title: string; subtitle: string; actions?: React.ReactNode }) {
  return <div className="page-head"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1><p>{subtitle}</p></div>{actions && <div className="head-actions">{actions}</div>}</div>
}

function Landing() {
  const navigate = useNavigate()
  return <div className="landing"><div className="landing-nav"><Brand /><span>Secure audio intelligence for modern teams</span></div><div className="hero-grid"><section className="hero-copy"><span className="eyebrow"><Sparkles /> AI-POWERED AUDIO WORKSPACE</span><h1>Transform every recording into <em>knowledge.</em></h1><p>Upload lectures, podcasts, interviews, and meetings. EchoScript creates searchable transcripts, precise subtitles, and polished AI recap videos.</p><div className="hero-actions"><button className="button primary" onClick={() => navigate('/dashboard')}>{mockAuth ? 'Enter demo workspace' : 'Continue with EchoScript'}<ChevronRight /></button><span><CheckCircle2 /> Secure Cognito authentication</span></div><div className="trust-row"><div><b>TXT</b><small>Clean transcripts</small></div><div><b>SRT + VTT</b><small>Timed subtitles</small></div><div><b>AI Video</b><small>Visual recaps</small></div></div></section><section className="hero-visual"><div className="orb orb-one" /><div className="orb orb-two" /><div className="demo-window"><div className="demo-top"><span /><span /><span /><small>Machine Learning Lecture.mp3</small></div><div className="sound-card"><div className="play-circle"><Play /></div><div className="wave-bars">{Array.from({ length: 34 }, (_, i) => <i key={i} style={{ height: `${18 + ((i * 17) % 48)}px` }} />)}</div><b>08:42</b></div><div className="transcript-card"><span><FileText /> Transcript ready</span><p>Machine learning systems improve their performance by learning patterns from data...</p><div><b>TXT</b><b>SRT</b><b>VTT</b><button><Download /></button></div></div><div className="floating-card"><WandSparkles /><div><b>AI recap rendering</b><span><i /></span></div><strong>74%</strong></div></div></section></div></div>
}

function Dashboard() {
  const { data: jobs = [], isLoading } = useJobs()
  const navigate = useNavigate()
  const [filter, setFilter] = useState('ALL')
  const completed = jobs.filter(job => job.status === 'TRANSCRIBED').length
  const running = jobs.filter(job => ['CREATED', 'UPLOADED', 'RUNNING'].includes(job.status)).length
  const videos = jobs.filter(job => job.video_status === 'DONE').length
  const visible = jobs.filter(job => filter === 'ALL' || (filter === 'COMPLETED' ? job.status === 'TRANSCRIBED' : job.status === filter)).slice(0, 5)
  const metrics = [{ icon: FileAudio, label: 'Total audio jobs', value: jobs.length, tone: 'orange' }, { icon: CheckCircle2, label: 'Completed transcripts', value: completed, tone: 'green' }, { icon: LoaderCircle, label: 'Currently processing', value: running, tone: 'blue' }, { icon: Film, label: 'Generated recap videos', value: videos, tone: 'purple' }]
  return <Shell><div className="page"><PageHead eyebrow="MONDAY, 19 OCTOBER" title="Welcome back, Alex" subtitle="Manage your audio, track transcription progress, and create AI-powered recaps." actions={<><button className="button secondary" onClick={() => navigate('/studio/video')}><WandSparkles />Open AI Studio</button><button className="button primary" onClick={() => navigate('/studio/transcribe')}><Plus />New transcription</button></>} />
    <div className="metrics">{metrics.map(({ icon: Icon, label, value, tone }) => <article className="metric-card" key={label}><div className={`metric-icon ${tone}`}><Icon /></div><div><strong>{isLoading ? '—' : value}</strong><span>{label}</span></div><MoreHorizontal /></article>)}</div>
    <section className="panel activity-panel"><div className="panel-head"><div><h2>Recent activity</h2><p>Your latest audio processing jobs</p></div><button className="text-button" onClick={() => navigate('/jobs')}>View all jobs <ChevronRight /></button></div><div className="tabs">{['ALL', 'RUNNING', 'COMPLETED', 'FAILED'].map(tab => <button className={filter === tab ? 'active' : ''} onClick={() => setFilter(tab)} key={tab}>{tab === 'ALL' ? 'All' : tab[0] + tab.slice(1).toLowerCase()}</button>)}</div>
      <div className="activity-list">{visible.length ? visible.map(job => <JobRow job={job} key={job.id} />) : <Empty title="Your studio is ready" body="Upload your first recording to generate a transcript and subtitles." action={<button className="button primary" onClick={() => navigate('/studio/transcribe')}><UploadCloud />Upload audio</button>} />}</div></section>
    <section className="section"><div className="section-title"><div><h2>Start creating</h2><p>Move from raw audio to useful content in a few clicks.</p></div></div><div className="quick-grid"><QuickCard tone="coral" icon={Mic2} title="Transcribe audio" body="Upload recordings and generate accurate transcripts and subtitles." action="Start transcription" onClick={() => navigate('/studio/transcribe')} /><QuickCard tone="violet" icon={Bot} title="Create AI recap" body="Turn a completed transcript into a concise presenter-led video." action="Open AI studio" onClick={() => navigate('/studio/video')} /><QuickCard tone="sage" icon={FolderOpen} title="Explore your library" body="Find every transcript, subtitle file, and generated recap." action="Browse files" onClick={() => navigate('/library')} /></div></section>
  </div></Shell>
}

function QuickCard({ tone, icon: Icon, title, body, action, onClick }: { tone: string; icon: React.ComponentType; title: string; body: string; action: string; onClick: () => void }) {
  return <button className={`quick-card ${tone}`} onClick={onClick}><span className="quick-art"><Icon /></span><div><span className="quick-icon"><Icon /></span><h3>{title}</h3><p>{body}</p><b>{action}<ChevronRight /></b></div></button>
}

function JobRow({ job }: { job: Job }) {
  const navigate = useNavigate()
  return <button className="job-row" onClick={() => navigate(`/jobs/${job.id}`)}><span className="file-icon"><FileAudio /></span><div className="job-main"><b>{job.filename}</b><span>{new Date(job.created_at).toLocaleString()} · {(job.size_bytes / 1_048_576).toFixed(1)} MB</span></div><StatusPill status={job.status} /><span className="job-action">{job.status === 'TRANSCRIBED' ? 'View results' : job.status === 'FAILED' ? 'Review error' : 'View progress'}<ChevronRight /></span></button>
}

function Transcribe() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [language, setLanguage] = useState('auto')
  const [progress, setProgress] = useState(0)
  const [stage, setStage] = useState('')
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const controller = useRef<AbortController | null>(null)
  const capabilities = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities })
  const submit = async () => {
    if (!file) return
    setError(''); setStage('Creating job')
    try {
      const created = await api.create(file, language)
      setStage('Uploading audio'); controller.current = new AbortController()
      await uploadFile(created.upload_url, file, created.upload_headers, setProgress, controller.current.signal)
      await api.completeUpload(created.job.id)
      setStage('Starting transcription'); await api.start(created.job.id)
      navigate(`/jobs/${created.job.id}`)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to start transcription'); setStage('') }
  }
  const choose = (candidate?: File) => {
    if (!candidate) return
    const extension = candidate.name.split('.').pop()?.toLowerCase()
    if (!['mp3', 'wav', 'm4a'].includes(extension || '')) return setError('Choose an MP3, WAV, or M4A audio file.')
    if (candidate.size > (capabilities.data?.max_upload_bytes || 262_144_000)) return setError('This file exceeds the configured upload limit.')
    setFile(candidate); setError(''); setProgress(0)
  }
  return <Shell><div className="page narrow"><PageHead eyebrow="AUDIO WORKSPACE" title="New transcription" subtitle="Upload your audio and let EchoScript handle the rest." />
    <div className="studio-layout"><section className="panel upload-panel"><div className="step-label"><span>1</span><div><h2>Add your audio</h2><p>Start with a recording, lecture, meeting, or podcast.</p></div></div>
      <div className={`dropzone ${file ? 'has-file' : ''}`} onClick={() => inputRef.current?.click()} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); choose(event.dataTransfer.files[0]) }}><input ref={inputRef} type="file" accept=".mp3,.wav,.m4a,audio/*" hidden onChange={event => choose(event.target.files?.[0])} />{file ? <><span className="selected-file"><FileAudio /></span><h3>{file.name}</h3><p>{(file.size / 1_048_576).toFixed(2)} MB · Ready to upload</p><div><button className="text-button">Replace file</button><button className="text-button danger" onClick={event => { event.stopPropagation(); setFile(null) }}>Remove</button></div></> : <><span className="upload-icon"><CloudUpload /></span><h3>Drag and drop your audio here</h3><p>or <b>browse files</b> from your device</p><small>MP3, WAV or M4A · Up to {Math.round((capabilities.data?.max_upload_bytes || 262_144_000) / 1_048_576)} MB</small></>}</div>
      {error && <div className="inline-error"><CircleAlert />{error}</div>}
      <div className="step-label options-step"><span>2</span><div><h2>Choose transcription language</h2><p>Your audio will produce a transcript and subtitle files only.</p></div></div><div className="option-grid"><label><span><Languages />Transcription language</span><select value={language} onChange={event => setLanguage(event.target.value)}>{(capabilities.data?.languages || [{ value: 'auto', label: 'Auto-detect' }, { value: 'en', label: 'English' }]).map(item => <option value={item.value} key={item.value}>{item.label}</option>)}</select></label><label className="toggle-option"><span><WandSparkles />AI video is a separate feature<small>After transcription, open AI Recap Studio whenever you want to create a HeyGen video.</small></span></label></div>
      {stage && <div className="upload-progress"><div><span>{stage}</span><b>{progress}%</b></div><span><i style={{ width: `${Math.max(progress, 8)}%` }} /></span><button onClick={() => controller.current?.abort()}>Cancel upload</button></div>}
      <div className="form-footer"><span><Zap /> Direct encrypted upload. No browser credentials are stored.</span><button className="button primary large" disabled={!file || !!stage} onClick={submit}>{stage ? <LoaderCircle className="spin" /> : <Sparkles />}{stage || 'Start transcription'}</button></div></section>
      <aside className="tip-card"><div className="tip-visual"><div className="mini-wave">{Array.from({ length: 18 }, (_, i) => <i key={i} style={{ height: `${12 + ((i * 13) % 34)}px` }} />)}</div><Headphones /></div><span>FOR BEST RESULTS</span><h3>Clear audio creates clearer knowledge.</h3><ul><li><Check />Use a quiet recording</li><li><Check />Keep speakers close to the mic</li><li><Check />Avoid overlapping conversations</li></ul></aside>
    </div></div></Shell>
}

function Jobs() {
  const { data: jobs = [], isLoading, refetch } = useJobs()
  const [tab, setTab] = useState('ALL')
  const [search, setSearch] = useState('')
  const filtered = jobs.filter(job => job.filename.toLowerCase().includes(search.toLowerCase()) && (tab === 'ALL' || (tab === 'COMPLETED' ? job.status === 'TRANSCRIBED' : tab === 'PROCESSING' ? ['CREATED', 'UPLOADED', 'RUNNING'].includes(job.status) : job.status === tab)))
  return <Shell><div className="page"><PageHead title="My Jobs" subtitle="All your audio processing activities in one place." actions={<button className="button primary" onClick={() => location.assign('/studio/transcribe')}><Plus />New transcription</button>} /><section className="panel jobs-panel"><div className="job-toolbar"><div className="tabs">{['ALL', 'PROCESSING', 'COMPLETED', 'FAILED'].map(item => <button key={item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item === 'ALL' ? 'All jobs' : item[0] + item.slice(1).toLowerCase()}</button>)}</div><div className="toolbar-actions"><label className="search"><Search /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search filename" /></label><button className="icon-button" onClick={() => refetch()}><RefreshCw /></button></div></div><div className="jobs-list">{isLoading ? Array.from({ length: 4 }, (_, i) => <div className="skeleton-row" key={i} />) : filtered.length ? filtered.map(job => <JobRow key={job.id} job={job} />) : <Empty title="No jobs match this view" body="Try another filter or upload a new recording." />}</div></section></div></Shell>
}

function JobDetail() {
  const { jobId = '' } = useParams()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const jobQuery = useQuery({ queryKey: ['job', jobId], queryFn: () => api.job(jobId), refetchInterval: query => query.state.data && (query.state.data.status === 'RUNNING' || ['PENDING', 'RENDERING'].includes(query.state.data.video_status)) ? 2500 : false })
  const videoMutation = useMutation({ mutationFn: () => api.video(jobId), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['job', jobId] }) })
  const job = jobQuery.data
  const audioUrl = useProtectedAsset(job?.outputs.audio)
  const videoUrl = useProtectedAsset(job?.outputs.video)
  if (jobQuery.isLoading) return <Shell><div className="page"><div className="detail-skeleton" /></div></Shell>
  if (!job) return <Shell><div className="page"><Empty title="Job not found" body="This job may have been removed or belongs to another user." /></div></Shell>
  const active = ['CREATED', 'UPLOADED', 'RUNNING'].includes(job.status)
  return <Shell><div className="page"><button className="back-link" onClick={() => navigate('/jobs')}><ArrowLeft />Back to my jobs</button><div className="detail-head"><div className="detail-file"><span><FileAudio /></span><div><h1>{job.filename}</h1><p>Uploaded {new Date(job.created_at).toLocaleString()} · {(job.size_bytes / 1_048_576).toFixed(2)} MB</p></div></div><StatusPill status={job.status} /></div>
    {active && <section className="processing-banner"><div className="processing-orb"><span /><Mic2 /></div><div><span>PROCESSING YOUR AUDIO</span><h2>{job.status === 'RUNNING' ? 'Transcribing spoken words…' : 'Preparing your recording…'}</h2><p>We’ll keep this page updated automatically. You can safely leave and come back later.</p><div className="indeterminate"><i /></div></div></section>}
    {job.status === 'FAILED' && <div className="error-banner"><CircleAlert /><div><b>Transcription could not be completed</b><p>{job.error_message || 'Review the audio file and try again.'}</p></div></div>}
    {job.status === 'TRANSCRIBED' && <div className="detail-grid"><section className="panel transcript-panel"><div className="panel-head"><div><span className="eyebrow">TRANSCRIPT</span><h2>Your audio, made searchable</h2></div><div><button className="button secondary small" onClick={() => navigator.clipboard.writeText(job.transcript_preview || '')}><Copy />Copy</button><DownloadFileButton path={job.outputs.transcript} className="button primary small"><Download />Download TXT</DownloadFileButton></div></div>{audioUrl && <audio controls src={audioUrl} />}<label className="transcript-search"><Search /><input placeholder="Search transcript" /></label><div className="transcript-copy"><p>{job.transcript_preview}</p></div></section><aside className="result-aside"><section className="panel"><h3>Download results</h3><p>Use your transcript wherever knowledge needs to travel.</p>{[['TXT', 'Plain text transcript', job.outputs.transcript], ['SRT', 'Timed subtitle file', job.outputs.srt], ['VTT', 'Web-ready captions', job.outputs.vtt]].map(([format, label, path]) => <DownloadFileButton key={format} path={path} className={`download-row ${!path ? 'disabled' : ''}`}><span><FileText /></span><div><b>{format}</b><small>{label}</small></div><Download /></DownloadFileButton>)}</section><section className="panel video-result"><span className="video-symbol"><WandSparkles /></span><h3>{job.video_status === 'DONE' ? 'Your recap is ready' : job.video_status === 'RENDERING' ? 'Rendering your recap' : 'Turn insight into a story'}</h3><p>Create a concise AI-presenter recap from this transcript.</p>{job.video_status === 'DONE' && job.outputs.video ? <><video controls src={videoUrl} /><DownloadFileButton path={job.outputs.video} className="button primary full"><Download />Download MP4</DownloadFileButton></> : job.video_status === 'RENDERING' || job.video_status === 'PENDING' ? <button className="button secondary full" disabled><LoaderCircle className="spin" />Video rendering</button> : <button className="button primary full" onClick={() => videoMutation.mutate()} disabled={videoMutation.isPending}><Sparkles />Generate recap video</button>}</section></aside></div>}
  </div></Shell>
}

function VideoStudio() {
  const { data: jobs = [] } = useJobs()
  const capabilities = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities })
  const completed = jobs.filter(job => job.status === 'TRANSCRIBED')
  const [selectedId, setSelectedId] = useState('')
  const selected = completed.find(job => job.id === selectedId)
  const [script, setScript] = useState('')
  const [avatar, setAvatar] = useState('demo-nova')
  const [voice, setVoice] = useState('demo-clear')
  const [step, setStep] = useState(1)
  const videoMutation = useMutation({ mutationFn: () => api.video(selectedId), onSuccess: () => setStep(4) })
  const proceed = () => { if (step === 1 && selected) setScript(selected.transcript_preview || ''); setStep(Math.min(4, step + 1)) }
  return <Shell><div className="page"><PageHead eyebrow="ECHOSCRIPT CREATIVE" title="AI Recap Studio" subtitle="Transform your transcripts into engaging AI-presenter videos." /><div className="workflow"><div className="workflow-steps">{['Choose transcript', 'Prepare script', 'Avatar & voice', 'Generate recap'].map((label, index) => <button key={label} className={step === index + 1 ? 'active' : step > index + 1 ? 'done' : ''} onClick={() => index + 1 <= step && setStep(index + 1)}><span>{step > index + 1 ? <Check /> : index + 1}</span><div><small>STEP {index + 1}</small><b>{label}</b></div></button>)}</div><section className="panel creator-panel">
      {step === 1 && <><div className="creator-head"><span><BookOpen /></span><div><h2>Choose a completed transcript</h2><p>Select the knowledge you want to turn into a visual recap.</p></div></div><div className="select-list">{completed.length ? completed.map(job => <button className={selectedId === job.id ? 'selected' : ''} key={job.id} onClick={() => setSelectedId(job.id)}><span><FileAudio /></span><div><b>{job.filename}</b><small>{new Date(job.created_at).toLocaleDateString()} · Transcript ready</small></div>{selectedId === job.id ? <CheckCircle2 /> : <span className="radio" />}</button>) : <Empty title="No completed transcripts yet" body="Finish a transcription first, then return to create a recap." />}</div></>}
      {step === 2 && <><div className="creator-head"><span><FileText /></span><div><h2>Shape the recap script</h2><p>Review the generated summary and make it sound like you.</p></div></div><label className="script-editor"><textarea value={script} onChange={event => setScript(event.target.value.slice(0, capabilities.data?.video.max_script_characters || 1500))} /><span>{script.length} / {capabilities.data?.video.max_script_characters || 1500} characters</span></label><button className="text-button" onClick={() => setScript(selected?.transcript_preview || '')}><RefreshCw />Restore generated summary</button></>}
      {step === 3 && <><div className="creator-head"><span><User /></span><div><h2>Choose a presenter</h2><p>Demo personas are replaced by backend-provided HeyGen IDs in production.</p></div></div><div className="avatar-grid">{(capabilities.data?.video.avatars || []).map((item, index) => <button key={item.id} onClick={() => setAvatar(item.id)} className={avatar === item.id ? 'selected' : ''}><span className={`avatar-art avatar-${index + 1}`}><User /></span><b>{item.name}</b><small>{item.role}</small>{avatar === item.id && <CheckCircle2 />}</button>)}</div><label className="voice-select"><span>Presenter voice</span><select value={voice} onChange={event => setVoice(event.target.value)}>{(capabilities.data?.video.voices || []).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button><Play />Preview</button></label></>}
      {step === 4 && <div className="review-card"><div className="review-visual"><span><Video /></span><div className="review-wave">{Array.from({ length: 20 }, (_, i) => <i key={i} style={{ height: `${10 + ((i * 11) % 38)}px` }} />)}</div></div><span className="eyebrow">READY TO CREATE</span><h2>Your recap is composed</h2><p>EchoScript will render the selected transcript with your presenter and voice. This may take several minutes with the production provider.</p><div className="review-summary"><div><FileAudio /><span><small>Transcript</small><b>{selected?.filename}</b></span></div><div><User /><span><small>Presenter</small><b>{avatar.replace('demo-', '')} · {voice.replace('demo-', '')}</b></span></div></div><button className="button primary large" onClick={() => videoMutation.mutate()} disabled={!selected || videoMutation.isPending}>{videoMutation.isPending ? <LoaderCircle className="spin" /> : <WandSparkles />}Generate recap video</button></div>}
      {step < 4 && <div className="creator-footer"><button className="button ghost" disabled={step === 1} onClick={() => setStep(step - 1)}>Back</button><button className="button primary" disabled={(step === 1 && !selectedId) || (step === 2 && !script.trim())} onClick={proceed}>Continue<ChevronRight /></button></div>}
    </section></div></div></Shell>
}

function Library() {
  const { data: jobs = [] } = useJobs()
  const [tab, setTab] = useState('ALL')
  const [grid, setGrid] = useState(true)
  const files = jobs.flatMap(job => [{ type: 'TRANSCRIPT', ext: 'TXT', path: job.outputs.transcript, job }, { type: 'SUBTITLE', ext: 'SRT', path: job.outputs.srt, job }, { type: 'SUBTITLE', ext: 'VTT', path: job.outputs.vtt, job }, { type: 'VIDEO', ext: 'MP4', path: job.outputs.video, job }]).filter(item => item.path && (tab === 'ALL' || item.type === tab))
  return <Shell><div className="page"><PageHead title="My Library" subtitle="Every transcript, subtitle, and recap—organized around its source audio." /><section className="panel library-panel"><div className="job-toolbar"><div className="tabs">{[['ALL', 'All files'], ['TRANSCRIPT', 'Transcripts'], ['SUBTITLE', 'Subtitles'], ['VIDEO', 'AI recap videos']].map(([value, label]) => <button className={tab === value ? 'active' : ''} onClick={() => setTab(value)} key={value}>{label}</button>)}</div><div className="view-toggle"><button className={grid ? 'active' : ''} onClick={() => setGrid(true)}><Grid2X2 /></button><button className={!grid ? 'active' : ''} onClick={() => setGrid(false)}><List /></button></div></div>{files.length ? <div className={grid ? 'file-grid' : 'file-list'}>{files.map((file, index) => <article className="file-card" key={`${file.job.id}-${file.ext}`}><div className={`file-preview ${file.ext === 'MP4' ? 'video' : ''}`}>{file.ext === 'MP4' ? <Film /> : <FileText />}<span>{file.ext}</span></div><div className="file-meta"><b>{file.job.filename.replace(/\.[^.]+$/, '')}</b><span>{file.type.toLowerCase()} · {new Date(file.job.updated_at).toLocaleDateString()}</span></div><DownloadFileButton path={file.path} className="icon-button" title="Download"><Download /></DownloadFileButton></article>)}</div> : <Empty title="Your library is waiting" body="Completed jobs will place transcripts, subtitles, and videos here automatically." />}</section></div></Shell>
}

function SettingsPage() {
  return <Shell><div className="page narrow"><PageHead title="Settings" subtitle="Manage your profile, workflow defaults, and session." /><div className="settings-layout"><aside className="settings-nav"><button className="active"><User />Profile</button><button><Settings />Preferences</button><button><Bell />Notifications</button></aside><section className="panel settings-panel"><div className="settings-section"><h2>Profile</h2><p>Identity details supplied by your authentication provider.</p><div className="profile-summary"><span>AM</span><div><b>Alex Morgan</b><small>alex@echoscript.local</small></div><button className="button secondary small">Manage account</button></div><div className="field-grid"><label><span>Full name</span><input value="Alex Morgan" readOnly /></label><label><span>Email address</span><input value="alex@echoscript.local" readOnly /></label><label><span>User ID</span><input value="demo-user-001" readOnly /></label></div></div><div className="settings-section"><h2>Preferences</h2><p>These non-sensitive defaults are stored in your browser.</p><div className="field-grid"><label><span>Default language</span><select><option>Auto-detect</option><option>English</option></select></label><label><span>Appearance</span><select><option>Light</option><option>System default</option></select></label></div><label className="toggle-option standalone"><span>Generate recap videos by default<small>You can always change this before uploading.</small></span><input type="checkbox" /><i /></label></div><div className="settings-section danger-zone"><h2>Session</h2><p>Signing out clears the active browser session.</p><button className="button secondary"><LogOut />Sign out</button></div></section></div></div></Shell>
}

function Unauthorized() { return <div className="center-page"><Brand /><CircleAlert /><h1>Access denied</h1><p>Your account cannot access this workspace.</p><a className="button primary" href="/">Return home</a></div> }
function NotFound() { return <div className="center-page"><Brand /><span className="big-number">404</span><h1>This page wandered off</h1><p>The link may be outdated or the page has moved.</p><a className="button primary" href="/dashboard">Back to dashboard</a></div> }

export default function App() {
  return <Routes><Route path="/" element={<Landing />} /><Route path="/auth/callback" element={<Navigate to="/dashboard" replace />} /><Route path="/dashboard" element={<Dashboard />} /><Route path="/studio/transcribe" element={<Transcribe />} /><Route path="/studio/video" element={<VideoStudio />} /><Route path="/jobs" element={<Jobs />} /><Route path="/jobs/:jobId" element={<JobDetail />} /><Route path="/library" element={<Library />} /><Route path="/settings" element={<SettingsPage />} /><Route path="/unauthorized" element={<Unauthorized />} /><Route path="*" element={<NotFound />} /></Routes>
}
