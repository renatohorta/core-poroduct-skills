# Agentic UI — Component Creation Pattern

## When to use
Create a new Generative UI component (React) + Copilot skill (Python) pair for the Agentic UI system.

## Two-sided pattern

### Backend: Copilot skill (`chat/skills/agentic_ui_skills.py`)

```python
@register_skill
class SomeSkill(BaseSkill):
    name = "skill_name"           # snake_case, used as tool name
    category = "Categoria"        # "Agentes", "Integrações", "Sistema"
    icon = "🎯"                   # Emoji for frontend display
    example_prompt = "..."        # Shown in skill cards
    description = "..."           # LLM sees this — be descriptive
    parameters = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
        },
        "required": ["param1"],
    }

    def execute(self, **kwargs) -> dict:
        # Process logic, query DB, etc.
        return {
            "component": "ComponentName",  # MUST match UI_REGISTRY key
            "props": { ... },              # Passed as props to React component
        }
```

### Frontend: React component (`src/components/generic-ui/ComponentName.tsx`)

```tsx
import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SomeIcon } from "lucide-react";

export const ComponentName = ({
  prop1,
  prop2,
  onAction,
}: {
  prop1: string;
  prop2?: number;
  onAction?: (action: string, payload?: any) => void;
}) => {
  return (
    <Card className="my-2">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <SomeIcon className="w-4 h-4" />
          Title
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* content */}
      </CardContent>
    </Card>
  );
};
```

### Registration (`src/components/generic-ui/registry.tsx`)

```tsx
import { ComponentName } from "./ComponentName";

const UI_REGISTRY: Record<string, React.FC<any>> = {
  ...existing,
  ComponentName,  // key = component name returned by skill
};
```

## Standard components (already exist)

| Component | File | Props |
|-----------|------|-------|
| PlaybookCard | `PlaybookCard.tsx` | name, description, category, icon, agentCount, taskCount, slug, onSelect |
| PlaybookList | `PlaybookList.tsx` | playbooks[], total, onSelect |
| IntegrationStatus | `IntegrationStatus.tsx` | playbookName, integrations[], allConnected, onConnect |
| WhatsAppQRCode | `WhatsAppQRCode.tsx` | qrCode, sessionId, expiresAt, onScanned, onRefresh |
| AssetUploader | `AssetUploader.tsx` | onUpload, maxFiles, accept |
| CrewProgress | `CrewProgress.tsx` | crewName, runId, status, totalTasks, completedTasks |
| DeliverableGallery | `DeliverableGallery.tsx` | crewName, deliverables[], total |
| ProposalPreview | `ProposalPreview.tsx` | title, pdfUrl, onDownload, onView |
| MetricsDashboard | `MetricsDashboard.tsx` | title, metrics[], period |

## SuggestPlaybook matching heuristics

When suggesting a playbook from a user briefing, use keyword matching:

| Keywords in briefing | Playbook slug |
|---------------------|---------------|
| marketing, campanha, divulgar, promover, redes sociais, instagram, tiktok, twitter | agency-campanha-marketing-multicanal |
| presença digital, esteticista, advogado, dentista, personal, profissional liberal, site, whatsapp, orçamento, proposta | agency-presenca-digital-profissional |
| lançamento, produto digital, curso, mentoria, ebook, saas, mvp, startup | agency-lancamento-produto-digital |
| feature, funcionalidade, enterprise, desenvolvimento, sistema, api, backend | agency-feature-enterprise |
| crise, emergência, urgente, reputação, comunicado, incidente, problema | agency-resposta-crise |

## Status icons for CrewProgress

```typescript
const STATUS_CONFIG = {
  QUEUED: { icon: Clock, color: "text-muted-foreground", label: "Na fila" },
  RUNNING: { icon: Loader2, color: "text-primary", label: "Executando" },
  DONE: { icon: CheckCircle2, color: "text-green-500", label: "Concluído" },
  COMPLETED: { icon: CheckCircle2, color: "text-green-500", label: "Concluído" },
  ERROR: { icon: XCircle, color: "text-destructive", label: "Erro" },
  WAITING_APPROVAL: { icon: AlertTriangle, color: "text-amber-500", label: "Aguardando aprovação" },
  REJECTED: { icon: XCircle, color: "text-destructive", label: "Rejeitado" },
};
```
