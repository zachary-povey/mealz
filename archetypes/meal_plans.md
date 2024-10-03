{{- $contentBaseName := .File.ContentBaseName -}}
{{- $date := $contentBaseName | time.AsTime -}}
{{- $endDate := $date.AddDate 0 0 6 -}}
---
title: Meal Plan for {{ $contentBaseName }} -> {{ $endDate.Format "2006-01-02" }}
date: {{ .Date }}
plan_start: {{ $contentBaseName }}
plan_end: {{ $endDate.Format "2006-01-02" }}
meals: []
---