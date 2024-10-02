{{- $contentBaseName := .File.ContentBaseName -}}
{{- $date := $contentBaseName | time.AsTime -}}
{{- $newDate := $date.AddDate 0 0 7 -}}
---
title: Meal Plan for {{ $contentBaseName }} -> {{ $newDate.Format "2006-01-02" }}
plan_start: {{ $contentBaseName }}
plan_end: {{ $newDate.Format "2006-01-02" }}
meals: []
---