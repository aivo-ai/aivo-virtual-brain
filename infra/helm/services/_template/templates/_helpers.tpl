{{/*
Expand the name of the chart.
*/}}
{{- define "aivo-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "aivo-service.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "aivo-service.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "aivo-service.labels" -}}
helm.sh/chart: {{ include "aivo-service.chart" . }}
{{ include "aivo-service.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "aivo-service.selectorLabels" -}}
app.kubernetes.io/name: {{ include "aivo-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "aivo-service.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "aivo-service.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Image repository
*/}}
{{- define "aivo-service.image" -}}
{{- $registry := .Values.global.imageRegistry | default "ghcr.io" }}
{{- $repository := .Values.global.imageRepository | default "aivo-ai/aivo-virtual-brain" }}
{{- $serviceName := include "aivo-service.name" . }}
{{- $tag := .Values.image.tag | default .Chart.AppVersion }}
{{- printf "%s/%s/%s:%s" $registry $repository $serviceName $tag }}
{{- end }}

{{/*
Vault annotations
*/}}
{{- define "aivo-service.vaultAnnotations" -}}
{{- if .Values.vault.enabled }}
vault.hashicorp.com/agent-inject: "true"
vault.hashicorp.com/role: {{ .Values.vault.role | default (include "aivo-service.name" .) | quote }}
vault.hashicorp.com/agent-pre-populate-only: "true"
{{- range $index, $secret := .Values.vault.secrets }}
vault.hashicorp.com/agent-inject-secret-{{ $index }}: {{ $secret.secretPath | quote }}
vault.hashicorp.com/agent-inject-template-{{ $index }}: |
{{ $secret.template | indent 2 }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Security context
*/}}
{{- define "aivo-service.securityContext" -}}
{{- toYaml .Values.podSecurityContext }}
{{- end }}

{{/*
Container security context
*/}}
{{- define "aivo-service.containerSecurityContext" -}}
{{- toYaml .Values.securityContext }}
{{- end }}

{{/*
Resource requests and limits
*/}}
{{- define "aivo-service.resources" -}}
{{- toYaml .Values.resources }}
{{- end }}
