import { useEffect, useRef, useState } from 'react'
import {
  Download,
  FileText,
  FolderUp,
  Loader2,
  Sparkles,
  ChevronDown,
} from 'lucide-react'
import {
  onboardingKitsApi,
  type OnboardingTemplate,
  type StagedOnboardingDraft,
} from '@/lib/uploads'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardBody } from '@/components/ui/card'
import { useToast } from '@/components/ui/toast'
import { OnboardingReviewModal } from './onboarding-review-modal'

interface OnboardingKitWidgetProps {
  tenantId?: string
  onStagedDraft?: (draft: StagedOnboardingDraft) => void
  onPublished?: (summary: any) => void
  compact?: boolean
}

export function OnboardingKitWidget({
  tenantId,
  onStagedDraft,
  onPublished,
  compact = false,
}: OnboardingKitWidgetProps) {
  const toast = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [templates, setTemplates] = useState<OnboardingTemplate[]>([])
  const [selectedVertical, setSelectedVertical] = useState<string>('real_estate')
  const [loadingTemplates, setLoadingTemplates] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [stagedDraft, setStagedDraft] = useState<StagedOnboardingDraft | null>(null)
  const [publishing, setPublishing] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)

  // Load available templates
  useEffect(() => {
    let active = true
    setLoadingTemplates(true)
    onboardingKitsApi
      .list()
      .then((res) => {
        if (active && res.templates) {
          setTemplates(res.templates)
        }
      })
      .catch((err) => {
        console.warn('Failed loading onboarding kits:', err)
      })
      .finally(() => {
        if (active) setLoadingTemplates(false)
      })
    return () => {
      active = false
    }
  }, [])

  const currentTemplate = templates.find((t) => t.vertical === selectedVertical) || templates[0]

  const handleDownload = (format: 'docx' | 'pdf') => {
    const slug = currentTemplate?.vertical || selectedVertical
    const url = `/api/admin/onboarding-kits/${slug}/${format}`
    window.open(url, '_blank')
    toast.push(`Downloading ${currentTemplate?.title || slug} ${format.toUpperCase()} template...`)
  }

  const handleFileUpload = async (file: File) => {
    setParsing(true)
    try {
      toast.push(`Parsing ${file.name} with local Ollama LLM...`)
      let draft: StagedOnboardingDraft
      if (tenantId && tenantId !== 'draft_tenant') {
        draft = await onboardingKitsApi.stageTenant(tenantId, file)
      } else {
        draft = await onboardingKitsApi.stageGlobal(file)
      }
      setStagedDraft(draft)
      if (onStagedDraft) {
        onStagedDraft(draft)
      }
      toast.push(`Successfully bifurcated ${draft.offerings.length} items and ${draft.faqs.length} FAQs!`)
    } catch (err: any) {
      console.error('Document parsing failed:', err)
      toast.push(`Parsing failed: ${err.message || 'Check document format and try again'}`)
    } finally {
      setParsing(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleConfirmPublish = async (finalDraft: StagedOnboardingDraft) => {
    const tid = tenantId || finalDraft.tenant_id
    if (!tid || tid === 'draft_tenant') {
      if (onStagedDraft) onStagedDraft(finalDraft)
      setStagedDraft(null)
      toast.push('Staged configuration saved to wizard!')
      return
    }

    setPublishing(true)
    try {
      const res = await onboardingKitsApi.publishTenant(tid, finalDraft)
      toast.push(`Published! ${res.summary.offerings_created} offerings & ${res.summary.kb_chunks_indexed} chunks indexed.`)
      setStagedDraft(null)
      if (onPublished) onPublished(res.summary)
    } catch (err: any) {
      toast.push(`Publishing failed: ${err.message || 'Server error'}`)
    } finally {
      setPublishing(false)
    }
  }

  return (
    <>
      <Card className="border-teal-500/30 bg-teal-500/[0.02]">
        <CardBody className="p-4 sm:p-5">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
            {/* Left: Template Downloader */}
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-md bg-teal-500/10 text-teal-600">
                  <Sparkles className="h-4 w-4" />
                </span>
                <h3 className="text-sm font-semibold text-surface-fg">
                  Predefined Onboarding Kit & AI Bifurcation
                </h3>
                <Badge variant="outline" className="border-teal-500/40 text-teal-700 bg-teal-500/10">
                  Local Ollama LLM
                </Badge>
              </div>
              <p className="text-xs text-surface-muted max-w-xl">
                Download the predefined DOCX or PDF template for your industry, fill in your property/product listings, WhatsApp menu, and FAQs, then upload it below for zero-touch configuration.
              </p>

              {/* Template Dropdown & Download Buttons */}
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowDropdown(!showDropdown)}
                    className="flex items-center gap-2 rounded-lg border border-surface-line bg-surface-card px-3 py-1.5 text-xs font-medium text-surface-fg hover:border-teal-500/50 transition"
                  >
                    <span>{currentTemplate?.icon || '🏢'}</span>
                    <span>{currentTemplate?.title || 'Select Industry'}</span>
                    <ChevronDown className="h-3 w-3 text-surface-muted" />
                  </button>

                  {showDropdown && (
                    <div className="absolute left-0 top-full z-30 mt-1 w-64 rounded-lg border border-surface-line bg-surface-card p-1 shadow-xl">
                      {templates.map((tpl) => (
                        <button
                          key={tpl.vertical}
                          type="button"
                          onClick={() => {
                            setSelectedVertical(tpl.vertical)
                            setShowDropdown(false)
                          }}
                          className={`flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs transition ${
                            selectedVertical === tpl.vertical
                              ? 'bg-teal-500/15 text-teal-700 font-medium'
                              : 'text-surface-fg hover:bg-surface-elevated'
                          }`}
                        >
                          <span>{tpl.icon}</span>
                          <span className="truncate">{tpl.title}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Download DOCX */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDownload('docx')}
                  icon={<Download className="h-3.5 w-3.5 text-blue-600" />}
                >
                  Download Word (.docx)
                </Button>

                {/* Download PDF */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDownload('pdf')}
                  icon={<FileText className="h-3.5 w-3.5 text-rose-600" />}
                >
                  Download PDF
                </Button>
              </div>
            </div>

            {/* Right: Upload Drop Area */}
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-teal-500/40 bg-teal-500/5 p-4 text-center sm:min-w-[280px]">
              <input
                ref={fileInputRef}
                type="file"
                accept=".docx,.pdf,.doc,.xlsx,.csv,.txt,.md"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) handleFileUpload(f)
                }}
              />

              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-teal-500/15 text-teal-600 mb-2">
                {parsing ? <Loader2 className="h-5 w-5 animate-spin" /> : <FolderUp className="h-5 w-5" />}
              </div>

              <p className="text-xs font-medium text-surface-fg">
                {parsing ? 'Bifurcating with local Ollama...' : 'Upload Completed Document'}
              </p>
              <p className="text-[10px] text-surface-muted mt-0.5">
                Drop filled PDF or DOCX file to auto-populate
              </p>

              <Button
                variant="primary"
                size="sm"
                loading={parsing}
                onClick={() => fileInputRef.current?.click()}
                className="mt-2 text-xs"
              >
                Upload & Bifurcate
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Review & Edit Modal */}
      {stagedDraft && (
        <OnboardingReviewModal
          draft={stagedDraft}
          onClose={() => setStagedDraft(null)}
          onConfirm={handleConfirmPublish}
          publishing={publishing}
        />
      )}
    </>
  )
}
