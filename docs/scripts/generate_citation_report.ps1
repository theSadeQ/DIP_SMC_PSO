Param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$docsRoot = Join-Path (Split-Path $PSScriptRoot -Parent) '.'
$csvPath = Join-Path $docsRoot 'citations.csv'
$reportPath = Join-Path $docsRoot 'citation_validation_report.json'

function Get-FileLines($Path) {
  try { Get-Content -LiteralPath $Path -ErrorAction Stop } catch { @() }
}

$citations = @()
$mdFiles = Get-ChildItem -LiteralPath $docsRoot -Recurse -File -Include *.md
foreach ($f in $mdFiles) {
  $i = 1
  foreach ($line in Get-FileLines $f.FullName) {
    $matches = [regex]::Matches($line, '\[CIT-(\d{3})\]')
    foreach ($m in $matches) {
      $citations += [pscustomobject]@{
        citation_id = "CIT-" + $m.Groups[1].Value
        doc_location = (Resolve-Path -Relative $f.FullName).Replace('\\','/') + ':' + $i
        doc_entity = $line.Trim()
      }
    }
    $i++
  }
}

$registry = @{}
if (Test-Path $csvPath) {
  $rows = Import-Csv -LiteralPath $csvPath
  foreach ($r in $rows) { $registry[$r.citation_id] = $r }
}

function Get-CodeLine($ref) {
  if ([string]::IsNullOrWhiteSpace($ref)) { return $null }
  $path = $ref
  $line = $null
  if ($ref -match '^(.*?):(\d+)$') { $path = $matches[1]; $line = [int]$matches[2] }
  $abs = Join-Path (Get-Location) $path
  $text = $null
  if ($line) {
    $lines = Get-FileLines $abs
    if ($lines.Count -ge $line) { $text = $lines[$line-1] }
  }
  return [pscustomobject]@{ path=$path.Replace('\\','/'); line=$line; text=$text }
}

$out = @()
foreach ($c in $citations) {
  $id = $c.citation_id
  $reg = $registry[$id]
  $codeRef = if ($reg) { $reg.code_reference } else { '' }
  $status = if ($reg) { if ($reg.status) { $reg.status } else { 'ok' } } else { 'missing_reference' }
  $code = Get-CodeLine $codeRef
  $validation = $status
  $proposed = $null
  $reason = ''
  if (-not $codeRef) {
    $validation = 'missing_reference'
    $reason = 'No code_reference in registry.'
  } elseif ($code -ne $null) {
    if (-not (Test-Path $code.path)) {
      $validation = 'missing_reference'
      $reason = 'Code reference path not found.'
    } else {
      if ($code.line) {
        if ($code.text -and $code.text.Contains("[$id]")) {
          $reason = 'Code line tagged with citation.'
        } else {
          $reason = 'Code line found; no inline tag present.'
        }
      } else {
        $reason = 'Code file present; line unspecified.'
      }
    }
  }
  if ($id -eq 'CIT-047') {
    $proposed = 'Update angle thresholds in docs to 0.35 rad (switch) and 0.4 rad (reentry) to match config and controller.'
  }
  if ($id -eq 'CIT-067' -and $validation -ne 'missing_reference') {
    $validation = 'inconsistent'
    $proposed = 'Clarify 20 ms as illustrative; tie to `hil.extra_latency_ms` without fixed limit.'
  }
  $out += [pscustomobject]@{
    citation_id = $id
    doc_entity = $c.doc_entity
    doc_location = $c.doc_location
    code_reference = if ($code -and $code.line) { "$($code.path):$($code.line)" } elseif ($code) { $code.path } else { $null }
    validation_status = $validation
    proposed_update = $proposed
    reasoning = $reason
  }
}

$json = $out | ConvertTo-Json -Depth 6
Set-Content -LiteralPath $reportPath -Value $json -Encoding UTF8
Write-Host "Wrote $reportPath"
