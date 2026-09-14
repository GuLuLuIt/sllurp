from pathlib import Path

path = Path("examples/fastapi/app.py")
text = path.read_text()
text = text.replace("from queue import Queue", "from queue import Empty, Full, Queue", 1)
text = text.replace("TAG_QUEUE = Queue()", "TAG_QUEUE = Queue(maxsize=1)", 1)
marker = "ACTIVE_CONNECTIONS = []\n\n\nasync def process_queue():"
helper = '''ACTIVE_CONNECTIONS = []


def _publish_latest_tags(tags):
    """Queue the newest batch without allowing an unbounded backlog."""
    while True:
        try:
            TAG_QUEUE.put_nowait(tags)
            return
        except Full:
            try:
                TAG_QUEUE.get_nowait()
            except Empty:
                continue


async def process_queue():'''
if marker not in text:
    raise SystemExit("queue helper insertion target not found")
text = text.replace(marker, helper, 1)
old = "    TAG_QUEUE.put(serializable_tags)"
if old not in text:
    raise SystemExit("queue put target not found")
path.write_text(text.replace(old, "    _publish_latest_tags(serializable_tags)", 1))
