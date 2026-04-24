$ffmpegPath = "C:\Users\tanma\Downloads\Dev Environments & Extracted\ffmpeg-8.0.1-essentials_build\bin"
$current = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($current -notlike "*ffmpeg*") {
    [Environment]::SetEnvironmentVariable("Path", $current + ";" + $ffmpegPath, "Machine")
    Write-Host "FFmpeg added to system PATH successfully."
} else {
    Write-Host "FFmpeg already in PATH."
}
