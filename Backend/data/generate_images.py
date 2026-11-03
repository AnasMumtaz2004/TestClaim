"""Generate sample images for ClaimPilot demo data."""
import sys
from pathlib import Path
from random import Random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json

# Run this from the Backend folder so .env is found.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.documents import blur_score, BLUR_THRESHOLD


def get_base_dir():
    """Get the base directory for sample images."""
    return Path(__file__).resolve().parent / "sample_images"


def seed_generators(claim_number, doc_type):
    """Create seeded random and numpy generators from a string."""
    seed_str = f"{claim_number}-{doc_type}"
    rng = Random(seed_str)
    seed_int = sum(ord(c) for c in seed_str)
    np_rng = np.random.default_rng(seed_int)
    return rng, np_rng


def draw_damage_photo(claim_number, doc_type):
    """Draw a damage photo with random shapes and grain."""
    rng, np_rng = seed_generators(claim_number, doc_type)

    img = Image.new("RGB", (800, 600))
    draw = ImageDraw.Draw(img)

    bg_r = rng.randint(100, 150)
    bg_g = rng.randint(100, 150)
    bg_b = rng.randint(100, 150)
    draw.rectangle([0, 0, 800, 600], fill=(bg_r, bg_g, bg_b))

    for _ in range(14):
        x1 = rng.randint(0, 700)
        y1 = rng.randint(0, 500)
        x2 = x1 + rng.randint(50, 150)
        y2 = y1 + rng.randint(50, 150)
        r = rng.randint(50, 200)
        g = rng.randint(50, 200)
        b = rng.randint(50, 200)
        draw.rectangle([x1, y1, x2, y2], fill=(r, g, b))

    for _ in range(8):
        x = rng.randint(50, 750)
        y = rng.randint(50, 550)
        r = rng.randint(20, 80)
        r_color = rng.randint(50, 200)
        g_color = rng.randint(50, 200)
        b_color = rng.randint(50, 200)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(r_color, g_color, b_color))

    img_array = np.array(img, dtype=np.float32)
    noise = np_rng.normal(0, 10, img_array.shape)
    noisy = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(noisy)

    return img


def generate_damage_photos():
    """Generate all damage photos for claims 1-12."""
    base_dir = get_base_dir()
    photos_dir = base_dir / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    count = 0

    for claim_num in range(1, 13):
        claim_number = f"CLM-2026-{claim_num:04d}"
        claim_dir = photos_dir / claim_number
        claim_dir.mkdir(parents=True, exist_ok=True)

        for doc_type in ["photo_front", "photo_rear", "photo_left", "photo_right", "photo_closeup"]:
            img = draw_damage_photo(claim_number, doc_type)
            path = claim_dir / f"{doc_type}.jpg"
            img.save(path, "JPEG", quality=85)
            count = count + 1

    return count


def duplicate_claim_11_photo():
    """Make CLM-2026-0011's photo_front a copy of CLM-2026-0002's."""
    base_dir = get_base_dir()
    src = base_dir / "photos" / "CLM-2026-0002" / "photo_front.jpg"
    dst = base_dir / "photos" / "CLM-2026-0011" / "photo_front.jpg"
    img = Image.open(src)
    img.save(dst, "JPEG", quality=60)


def check_blur_scores():
    """Check blur scores and print any below threshold."""
    base_dir = get_base_dir()
    photos_dir = base_dir / "photos"

    print("\nBlur scores below threshold:")
    for claim_dir in sorted(photos_dir.iterdir()):
        if not claim_dir.is_dir():
            continue
        for photo in sorted(claim_dir.glob("*.jpg")):
            img = Image.open(photo)
            score = blur_score(img)
            if score < BLUR_THRESHOLD:
                print(f"  {photo.relative_to(base_dir)}: {score:.1f}")


def generate_estimate_bills():
    """Generate 6 estimate bills as PNG images."""
    base_dir = get_base_dir()
    bills_dir = base_dir / "bills"
    bills_dir.mkdir(parents=True, exist_ok=True)

    bills_data = [
        {"id": 1, "metal": 40000, "other": 10000, "labour": 15000, "garage": "City Auto Works", "wrong_total": False},
        {"id": 2, "metal": 22000, "other": 5000, "labour": 9000, "garage": "Sharma Motors", "wrong_total": False},
        {"id": 3, "metal": 18000, "other": 4000, "labour": 8000, "garage": "Delhi Car Care", "wrong_total": False},
        {"id": 4, "metal": 55000, "other": 12000, "labour": 20000, "garage": "Prime Garage", "wrong_total": True},
        {"id": 5, "metal": 26000, "other": 6000, "labour": 10000, "garage": "Shree Auto Repairs", "wrong_total": False},
        {"id": 6, "metal": 30000, "other": 8000, "labour": 12000, "garage": "City Auto Works", "wrong_total": False},
    ]

    truth_list = []

    for bill in bills_data:
        bill_id = bill["id"]
        metal = bill["metal"]
        other = bill["other"]
        labour = bill["labour"]
        garage = bill["garage"]
        wrong_total = bill["wrong_total"]

        total = metal + other + labour
        stated_total = total + 5000 if wrong_total else total

        claim_ref = f"CLM-2026-{(bill_id % 12) + 1:04d}"
        date_str = "2026-01-15"

        img = Image.new("RGB", (900, 1200), color="white")
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.load_default(26)
        except:
            font = ImageFont.load_default()

        y = 50
        draw.text((50, y), "ESTIMATE", fill="black", font=font)
        y = y + 50

        draw.text((50, y), f"Garage: {garage}", fill="black", font=font)
        y = y + 40

        draw.text((50, y), f"Date: {date_str}", fill="black", font=font)
        y = y + 40

        draw.text((50, y), f"Claim: {claim_ref}", fill="black", font=font)
        y = y + 60

        draw.text((50, y), f"Metal parts: Rs. {metal:,}", fill="black", font=font)
        y = y + 40

        draw.text((50, y), f"Other parts: Rs. {other:,}", fill="black", font=font)
        y = y + 40

        draw.text((50, y), f"Labour: Rs. {labour:,}", fill="black", font=font)
        y = y + 60

        draw.text((50, y), f"Total: Rs. {stated_total:,}", fill="black", font=font)

        filename = f"bill_{bill_id:02d}.png"
        path = bills_dir / filename
        img.save(path, "PNG")

        bill_entry = {
            "file": filename,
            "garage": garage,
            "date": date_str,
            "claim_reference": claim_ref,
            "items": [
                {"label": "Metal parts", "amount": metal},
                {"label": "Other parts", "amount": other},
                {"label": "Labour", "amount": labour},
            ],
            "stated_total": stated_total,
            "total_is_wrong": wrong_total,
            "variants": [],
        }

        if bill_id <= 3:
            blur_filename = f"bill_{bill_id:02d}_blur.png"
            img_blur = img.filter(ImageFilter.GaussianBlur(radius=2.5))
            img_blur.save(bills_dir / blur_filename, "PNG")
            bill_entry["variants"].append(blur_filename)

            rotated_filename = f"bill_{bill_id:02d}_rotated.png"
            img_rotated = img.rotate(3, expand=True, fillcolor="white")
            img_rotated.save(bills_dir / rotated_filename, "PNG")
            bill_entry["variants"].append(rotated_filename)

            shadow_filename = f"bill_{bill_id:02d}_shadow.jpg"
            img_array = np.array(img, dtype=np.float32)
            gradient = np.linspace(1.0, 0.55, 900)
            gradient_2d = gradient[np.newaxis, :]
            gradient_3d = np.dstack([gradient_2d] * 3)
            shadowed = img_array * gradient_3d
            shadowed = np.clip(shadowed, 0, 255).astype(np.uint8)
            img_shadow = Image.fromarray(shadowed)
            img_shadow.save(bills_dir / shadow_filename, "JPEG", quality=80)
            bill_entry["variants"].append(shadow_filename)

        truth_list.append(bill_entry)

    truth_path = bills_dir / "bills_truth.json"
    with open(truth_path, "w") as f:
        json.dump(truth_list, f, indent=2)

    return len(bills_data)


def generate_extras():
    """Generate sharp and blurry test photos."""
    base_dir = get_base_dir()
    extras_dir = base_dir / "extras"
    extras_dir.mkdir(parents=True, exist_ok=True)

    rng = Random("extras")
    img = Image.new("RGB", (800, 600))
    draw = ImageDraw.Draw(img)

    bg_r = rng.randint(100, 150)
    draw.rectangle([0, 0, 800, 600], fill=(bg_r, bg_r, bg_r))

    for _ in range(14):
        x1 = rng.randint(0, 700)
        y1 = rng.randint(0, 500)
        x2 = x1 + rng.randint(50, 150)
        y2 = y1 + rng.randint(50, 150)
        r = rng.randint(50, 200)
        draw.rectangle([x1, y1, x2, y2], fill=(r, r, r))

    for _ in range(8):
        x = rng.randint(50, 750)
        y = rng.randint(50, 550)
        r = rng.randint(20, 80)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(r, r, r))

    img_array = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, 10, img_array.shape)
    noisy = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(noisy)

    img.save(extras_dir / "sharp_photo.jpg", "JPEG", quality=85)

    img_blur = img.filter(ImageFilter.GaussianBlur(radius=8))
    img_blur.save(extras_dir / "blurry_photo.jpg", "JPEG", quality=85)


def main():
    """Generate all sample images."""
    base_dir = get_base_dir()
    base_dir.mkdir(parents=True, exist_ok=True)

    print("Generating damage photos...")
    photo_count = generate_damage_photos()
    print(f"  Wrote {photo_count} damage photos")

    print("\nDuplicating claim 11 photo...")
    duplicate_claim_11_photo()

    check_blur_scores()

    print("\nGenerating estimate bills...")
    bill_count = generate_estimate_bills()
    print(f"  Wrote {bill_count} bills")

    print("\nGenerating extras...")
    generate_extras()
    print(f"  Wrote 2 extras")

    print("\nDone generating images.")


if __name__ == "__main__":
    main()