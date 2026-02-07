import yt_dlp

def download_song(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'song.%(ext)s',
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(f"ytsearch1:{query}", download=True)

    return "song.mp3"
