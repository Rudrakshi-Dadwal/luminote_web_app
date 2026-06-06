#!/usr/bin/env python
from youtube_transcript_api import YouTubeTranscriptApi
import json

video_id = 'TYhNHX372ek'
try:
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)
    # Convert transcript snippets to dictionaries
    segments = [{'start': seg.start, 'duration': seg.duration, 'text': seg.text} for seg in transcript]
    print(json.dumps(segments, indent=2))
except Exception as e:
    import traceback
    print(f'Error: {type(e).__name__}: {e}')
    traceback.print_exc()
