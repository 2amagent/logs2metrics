{{- define "log-triage.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "log-triage.fullname" -}}
{{- .Release.Name -}}
{{- end -}}

{{- define "log-triage.labels" -}}
app.kubernetes.io/name: {{ include "log-triage.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "log-triage.selectorLabels" -}}
app.kubernetes.io/name: {{ include "log-triage.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "log-triage.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "log-triage.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "log-triage.s3SecretName" -}}
{{- if .Values.objectStore.s3.existingSecret -}}
{{- .Values.objectStore.s3.existingSecret -}}
{{- else -}}
{{- printf "%s-s3-creds" (include "log-triage.fullname" .) -}}
{{- end -}}
{{- end -}}
