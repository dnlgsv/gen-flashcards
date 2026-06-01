"""Tests for collecting media referenced by generated Anki cards."""

from src.anki_utils import referenced_media_files


def test_referenced_media_files_only_includes_card_references(temp_dir):
    audio_dir = temp_dir / "audio"
    images_dir = temp_dir / "images"
    audio_dir.mkdir()
    images_dir.mkdir()

    used_audio = audio_dir / "apple_expression.mp3"
    stale_audio = audio_dir / "old_word.mp3"
    used_image = images_dir / "apple.png"
    stale_image = images_dir / "old_word.png"
    for path in (used_audio, stale_audio, used_image, stale_image):
        path.write_bytes(b"media")

    media_files = referenced_media_files(
        [
            {
                "audio_expression": "[sound:apple_expression.mp3]",
                "image": '<img src="apple.png">',
            }
        ],
        audio_dir=audio_dir,
        images_dir=images_dir,
    )

    assert media_files == [str(used_audio), str(used_image)]
