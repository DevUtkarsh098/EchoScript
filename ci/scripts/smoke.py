"""Fresh authenticated smoke job. Never print tokens, presigned URLs, or transcripts."""
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

API = 'https://ec-4762c5d9c1fa4c50a19bed3b76373799.ecs.us-west-2.on.aws'
FRONTEND = 'https://dtdd5d335m3k2.cloudfront.net'
EXECUTION_PREFIX = 'arn:aws:states:us-west-2:598391748654:execution:echoscript-prod-transcription:'


def checked(response, status=200):
    if response.status_code != status:
        raise RuntimeError(f'Unexpected HTTP status {response.status_code}')
    return response


def run():
    evidence = {'image_tag': os.environ['IMAGE_TAG'], 'build_url': os.getenv('BUILD_URL', ''), 'status': 'failed'}
    try:
        public = requests.Session()
        checked(public.get(FRONTEND, timeout=30))
        readiness_deadline = time.monotonic() + 600
        while time.monotonic() < readiness_deadline:
            try:
                health = public.get(API + '/health', timeout=30)
                ready = public.get(API + '/ready', timeout=30)
                version = public.get(API + '/version', timeout=30)
                if (health.status_code == ready.status_code == version.status_code == 200
                        and health.json() == {'status': 'ok'} and version.json().get('commit') == os.environ['IMAGE_TAG']):
                    break
            except requests.RequestException:
                pass
            time.sleep(10)
        else:
            raise TimeoutError('API did not converge to the requested image')
        assert public.get(API + '/api/jobs', timeout=30).status_code == 401
        token = Path(os.environ['SMOKE_TOKEN_FILE']).read_text().strip()
        if not token or '\n' in token:
            raise ValueError('Invalid external smoke token')
        audio = Path(os.environ['SMOKE_AUDIO_FILE']).read_bytes()
        if not audio or len(audio) > 5_000_000:
            raise ValueError('Use an approved short spoken WAV fixture under 5 MB')
        session = requests.Session()
        session.headers['Authorization'] = f'Bearer {token}'
        created = checked(session.post(API + '/api/jobs', json={
            'filename': 'jenkins-acceptance.wav', 'content_type': 'audio/wav',
            'size_bytes': len(audio), 'language': 'en', 'generate_video': False,
        }, timeout=30), 201).json()
        job_id = created['job']['id']
        evidence['job_id'] = job_id
        target = urlparse(created['upload_url'])
        assert target.scheme == 'https' and target.hostname == 'echoscript-598391748654-prod-input.s3.us-west-2.amazonaws.com'
        # The bearer token must NEVER be sent to S3.
        checked(public.put(created['upload_url'], data=audio, headers=created['upload_headers'], timeout=90))
        checked(session.post(f'{API}/api/jobs/{job_id}/upload-complete', timeout=30))
        checked(session.post(f'{API}/api/jobs/{job_id}/start', timeout=30))
        deadline = time.monotonic() + 900
        execution = EXECUTION_PREFIX + job_id
        while time.monotonic() < deadline:
            job = checked(session.get(f'{API}/api/jobs/{job_id}', timeout=30)).json()
            if job['status'] == 'FAILED':
                raise RuntimeError('Transcription smoke job failed')
            if job['status'] == 'TRANSCRIBED':
                workflow = subprocess.run(['aws', 'stepfunctions', 'describe-execution', '--execution-arn', execution,
                                           '--query', 'status', '--output', 'text'], capture_output=True, text=True, check=True).stdout.strip()
                if workflow == 'SUCCEEDED':
                    break
                if workflow in {'FAILED', 'TIMED_OUT', 'ABORTED'}:
                    raise RuntimeError('Transcription workflow failed')
            time.sleep(10)
        else:
            raise TimeoutError('Fresh job/workflow did not complete within 15 minutes')
        outputs = {}
        for filename in ('transcript.txt', 'subtitles.srt', 'subtitles.vtt'):
            # Fetch redirect manually to avoid forwarding Authorization to object storage.
            response = session.get(f'{API}/api/jobs/{job_id}/files/{filename}', allow_redirects=False, timeout=30)
            checked(response, 307)
            location = response.headers['Location']
            parsed = urlparse(location)
            assert parsed.scheme == 'https' and parsed.hostname == 'echoscript-598391748654-prod-output.s3.us-west-2.amazonaws.com'
            content = checked(public.get(location, timeout=30)).content
            text = content.decode('utf-8').strip()
            assert text
            if filename.endswith(('.srt', '.vtt')):
                assert '-->' in text
            if filename.endswith('.vtt'):
                assert text.startswith('WEBVTT')
            outputs[filename] = {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
        evidence.update(status='passed', execution_arn=execution, workflow='SUCCEEDED', outputs=outputs)
    finally:
        Path('ci-artifacts').mkdir(exist_ok=True)
        Path('ci-artifacts/smoke-result.json').write_text(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    try:
        run()
    except Exception:
        # HTTP exception strings can include signed URLs. Keep failures value-free.
        raise SystemExit('Authenticated smoke failed. See value-free smoke-result.json and restricted service logs.')
