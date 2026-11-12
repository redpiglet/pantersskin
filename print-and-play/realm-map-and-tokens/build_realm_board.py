#!/usr/bin/env python3
"""Build the Georgian 7-Realm Map Board (A3 + 2xA4 split) and Character/Item Token sheets.

Uses macOS CoreGraphics, AppKit, CoreText, and PDFKit with the project's cached
SF Georgian fonts and selected high-resolution character portraits (downsampled to
360x360 px = >320 DPI at 28 mm token size for compact PDF output).
"""

import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHAR_DECK = ROOT / "print-and-play" / "character-deck"
OUT = ROOT / "output" / "realm-map-and-tokens"
OUT.mkdir(parents=True, exist_ok=True)

BOARD_DATA = json.loads((HERE / "realm-board-data.ka.json").read_text())
PORTRAIT_MANIFEST = json.loads((CHAR_DECK / "portrait-manifest.json").read_text())
DISPLAY_COPY = json.loads((CHAR_DECK / "display-copy.ka.json").read_text())
CHAR_CARDS = json.loads((ROOT / "data" / "character-cards.json").read_text())["characters"]
CHAR_BY_ID = {c["id"]: c for c in CHAR_CARDS}

REALM_COLORS = {r["id"]: r["color"] for r in BOARD_DATA["realms"]}
REALM_NAMES = {r["id"]: r["name"] for r in BOARD_DATA["realms"]}
REALM_SHORT_NAMES = {
    "arabia": "არაბეთი",
    "wilderness": "დევთა ქვაბი",
    "india": "ინდოეთი",
    "khataveti": "ხატაეთი",
    "mulgazanzar": "მულღაზანზარი",
    "gulansharo": "გულანშარო",
    "kajeti": "ქაჯეთის ციხე",
}

CHAR_HOME_REALM = {
    "avtandil": "arabia",
    "tariel": "wilderness",
    "nestan": "india",
    "tinatin": "arabia",
    "asmat": "wilderness",
    "pridon": "mulgazanzar",
    "fatman": "gulansharo",
    "rostevan": "arabia",
    "shermadin": "arabia",
    "sograt": "arabia",
    "parsadan": "india",
    "saridan": "india",
    "davari": "india",
    "khvarazmsha": "india",
    "ramaz": "khataveti",
    "usen": "gulansharo",
    "chashnagiri": "gulansharo",
    "surkhavi": "gulansharo",
    "dulardukht": "kajeti",
    "rosan": "kajeti",
    "rustaveli": "arabia",
}

PAINTED_CHARACTERS = []
for item in PORTRAIT_MANIFEST["portraits"]:
    cid = item["character_id"]
    if item["asset"] and item["status"] != "generic_silhouette":
        copy = DISPLAY_COPY[cid]
        rid = CHAR_HOME_REALM[cid]
        PAINTED_CHARACTERS.append({
            "id": cid,
            "name": copy["name"],
            "short_name": copy.get("short_name", copy["name"]),
            "role": copy["role"].split(";")[0],
            "realm_id": rid,
            "realm_name": REALM_NAMES[rid],
            "realm_short": REALM_SHORT_NAMES[rid],
            "color": REALM_COLORS[rid],
            "asset": str(ROOT / item["asset"]),
            "chapters_count": len(CHAR_BY_ID[cid]["chapter_presence"]["included_chapters"]),
        })
assert len(PAINTED_CHARACTERS) == 21, len(PAINTED_CHARACTERS)

OBJC_BUILDER = r"""
#import <Foundation/Foundation.h>
#import <AppKit/AppKit.h>
#import <PDFKit/PDFKit.h>
#import <CoreText/CoreText.h>

static void registerFont(NSString *path) {
    NSURL *url = [NSURL fileURLWithPath:path];
    CTFontManagerRegisterFontsForURL((__bridge CFURLRef)url, kCTFontManagerScopeProcess, NULL);
}

static NSColor *colorFromHex(NSString *hex, CGFloat alpha) {
    NSString *clean = [hex stringByReplacingOccurrencesOfString:@"#" withString:@""];
    unsigned int rgb = 0;
    [[NSScanner scannerWithString:clean] scanHexInt:&rgb];
    return [NSColor colorWithSRGBRed:((rgb >> 16) & 0xFF) / 255.0
                               green:((rgb >> 8) & 0xFF) / 255.0
                                blue:(rgb & 0xFF) / 255.0
                               alpha:alpha];
}

static NSFont *georgianFont(CGFloat size, BOOL bold) {
    NSFont *f = [NSFont fontWithName:(bold ? @"SFGeorgian-Semibold" : @"SFGeorgian-Regular") size:size];
    if (!f) f = bold ? [NSFont boldSystemFontOfSize:size] : [NSFont systemFontOfSize:size];
    return f;
}

static void drawText(NSString *text, CGFloat x, CGFloat y, CGFloat size, BOOL bold, NSColor *color, NSString *align) {
    if (!text) return;
    NSDictionary *attrs = @{
        NSFontAttributeName: georgianFont(size, bold),
        NSForegroundColorAttributeName: color
    };
    NSSize s = [text sizeWithAttributes:attrs];
    CGFloat dx = x;
    if ([align isEqualToString:@"center"]) dx -= s.width / 2.0;
    else if ([align isEqualToString:@"right"]) dx -= s.width;
    [text drawAtPoint:NSMakePoint(dx, y) withAttributes:attrs];
}

static CGFloat drawWrappedText(NSString *text, CGFloat x, CGFloat top, CGFloat width, CGFloat size, CGFloat leading, BOOL bold, NSColor *color, NSString *align) {
    if (!text || [text length] == 0) return top;
    NSMutableParagraphStyle *pStyle = [[NSMutableParagraphStyle alloc] init];
    pStyle.minimumLineHeight = leading;
    pStyle.maximumLineHeight = leading;
    if ([align isEqualToString:@"center"]) pStyle.alignment = NSTextAlignmentCenter;
    else if ([align isEqualToString:@"right"]) pStyle.alignment = NSTextAlignmentRight;
    else pStyle.alignment = NSTextAlignmentLeft;

    NSDictionary *attrs = @{
        NSFontAttributeName: georgianFont(size, bold),
        NSForegroundColorAttributeName: color,
        NSParagraphStyleAttributeName: pStyle
    };
    NSRect rect = [text boundingRectWithSize:NSMakeSize(width, 2000)
                                     options:NSStringDrawingUsesLineFragmentOrigin | NSStringDrawingUsesFontLeading
                                  attributes:attrs];
    CGFloat h = ceil(rect.size.height);
    [text drawInRect:NSMakeRect(x, top - h, width, h) withAttributes:attrs];
    return top - h;
}

static void fillRoundRect(CGContextRef ctx, CGRect r, CGFloat rad, NSColor *fill, NSColor *stroke, CGFloat lw) {
    NSBezierPath *p = [NSBezierPath bezierPathWithRoundedRect:NSRectFromCGRect(r) xRadius:rad yRadius:rad];
    if (fill) {
        [fill setFill];
        [p fill];
    }
    if (stroke && lw > 0) {
        [stroke setStroke];
        [p setLineWidth:lw];
        [p stroke];
    }
}

static NSImage *downsampledPortrait(NSString *path, int px) {
    NSImage *src = [[NSImage alloc] initWithContentsOfFile:path];
    if (!src) return nil;
    NSBitmapImageRep *rep = [[NSBitmapImageRep alloc]
        initWithBitmapDataPlanes:NULL
                      pixelsWide:px
                      pixelsHigh:px
                   bitsPerSample:8
                 samplesPerPixel:4
                        hasAlpha:YES
                        isPlanar:NO
                  colorSpaceName:NSDeviceRGBColorSpace
                     bytesPerRow:0
                    bitsPerPixel:0];
    NSGraphicsContext *nsCtx = [NSGraphicsContext graphicsContextWithBitmapImageRep:rep];
    [NSGraphicsContext saveGraphicsState];
    [NSGraphicsContext setCurrentContext:nsCtx];
    [nsCtx setImageInterpolation:NSImageInterpolationHigh];
    [src drawInRect:NSMakeRect(0, 0, px, px) fromRect:NSZeroRect operation:NSCompositingOperationSourceOver fraction:1.0];
    [NSGraphicsContext restoreGraphicsState];
    NSImage *out = [[NSImage alloc] initWithSize:NSMakeSize(px, px)];
    [out addRepresentation:rep];
    return out;
}

static void drawRouteCurve(CGContextRef ctx, CGPoint p1, CGPoint p2, CGPoint ctrl, BOOL isSea) {
    CGContextSaveGState(ctx);
    NSColor *col = isSea ? colorFromHex(@"#1E6F7D", 0.85) : colorFromHex(@"#8B4513", 0.85);
    [col setStroke];
    CGContextSetLineWidth(ctx, isSea ? 2.2 : 2.5);
    if (isSea) {
        CGFloat dash[2] = {6.0, 4.0};
        CGContextSetLineDash(ctx, 0, dash, 2);
    }
    CGContextMoveToPoint(ctx, p1.x, p1.y);
    CGContextAddQuadCurveToPoint(ctx, ctrl.x, ctrl.y, p2.x, p2.y);
    CGContextStrokePath(ctx);
    CGContextRestoreGState(ctx);
}

static void drawRoutePill(CGContextRef ctx, CGFloat mx, CGFloat my, BOOL isSea, NSString *label) {
    NSColor *col = isSea ? colorFromHex(@"#1E6F7D", 0.92) : colorFromHex(@"#8B4513", 0.92);
    NSDictionary *attrs = @{NSFontAttributeName: georgianFont(6.3, YES)};
    NSSize ts = [label sizeWithAttributes:attrs];
    CGRect pill = CGRectMake(mx - ts.width / 2.0 - 5.0, my - 6.2, ts.width + 10.0, 12.4);
    fillRoundRect(ctx, pill, 5.5, colorFromHex(@"#F8F5EC", 0.96), col, 0.8);
    drawText(label, mx, my - 3.8, 6.3, YES, col, @"center");
}

static void drawTokenSlot(CGContextRef ctx, CGFloat cx, CGFloat cy, CGFloat radius, NSColor *accent, NSString *hint, int slotNum) {
    CGContextSaveGState(ctx);
    [colorFromHex(@"#FFFFFF", 0.9) setFill];
    NSBezierPath *circle = [NSBezierPath bezierPathWithOvalInRect:NSMakeRect(cx - radius, cy - radius, radius * 2, radius * 2)];
    [circle fill];

    [accent setStroke];
    CGFloat dash[2] = {3.0, 2.5};
    [circle setLineDash:dash count:2 phase:0];
    [circle setLineWidth:1.1];
    [circle stroke];

    NSBezierPath *inner = [NSBezierPath bezierPathWithOvalInRect:NSMakeRect(cx - radius + 3, cy - radius + 3, (radius - 3) * 2, (radius - 3) * 2)];
    [colorFromHex(@"#A58958", 0.45) setStroke];
    [inner setLineWidth:0.5];
    [inner stroke];

    drawText([NSString stringWithFormat:@"ფიშკა %d", slotNum], cx, cy + 5.5, 5.6, YES, colorFromHex(@"#647168", 0.85), @"center");
    if (hint && [hint length] > 0) {
        CGFloat fSize = ([hint length] >= 10) ? 5.5 : 6.0;
        drawWrappedText(hint, cx - radius + 2.5, cy + 2.5, (radius - 2.5) * 2, fSize, 6.8, YES, accent, @"center");
    } else {
        drawText(@"თავისუფალი", cx, cy - 5.5, 5.5, NO, colorFromHex(@"#88928A", 0.8), @"center");
    }
    CGContextRestoreGState(ctx);
}

static void drawRealmBox(CGContextRef ctx, CGRect box, NSDictionary *realm, NSDictionary *charNames) {
    NSColor *accent = colorFromHex(realm[@"color"], 1.0);
    NSColor *fill = colorFromHex(realm[@"fill"], 0.96);
    NSColor *gold = colorFromHex(@"#A58958", 1.0);
    NSColor *ink = colorFromHex(@"#203D37", 1.0);

    fillRoundRect(ctx, box, 10.0, fill, accent, 2.0);
    fillRoundRect(ctx, CGRectInset(box, 3.5, 3.5), 7.5, nil, gold, 0.6);

    CGRect headerRect = CGRectMake(box.origin.x + 3.5, box.origin.y + box.size.height - 35.0, box.size.width - 7.0, 31.5);
    fillRoundRect(ctx, headerRect, 6.5, accent, nil, 0);

    NSString *title = [NSString stringWithFormat:@"%@. %@", realm[@"number"], realm[@"name"]];
    CGFloat titleSize = ([title length] > 16) ? 9.4 : 10.6;
    drawText(title, box.origin.x + 10.0, box.origin.y + box.size.height - 18.0, titleSize, YES, [NSColor whiteColor], @"left");
    drawText(realm[@"chapters"], box.origin.x + box.size.width - 10.0, box.origin.y + box.size.height - 17.5, 6.3, YES, colorFromHex(@"#FFE8B3", 1.0), @"right");
    drawText(realm[@"subtitle"], box.origin.x + 10.0, box.origin.y + box.size.height - 30.0, 6.4, NO, colorFromHex(@"#F8F5EC", 0.92), @"left");

    CGFloat y = box.origin.y + box.size.height - 40.0;
    NSArray *events = realm[@"key_events"];
    for (NSString *ev in events) {
        NSString *bullet = [NSString stringWithFormat:@"• %@", ev];
        y = drawWrappedText(bullet, box.origin.x + 9.0, y, box.size.width - 18.0, 6.4, 7.9, NO, ink, @"left") - 1.2;
    }

    NSArray *starters = realm[@"starting_tokens"];
    int slots = [realm[@"token_slots"] intValue];
    CGFloat slotAreaTop = box.origin.y + box.size.height - 91.0;
    CGFloat slotAreaBottom = box.origin.y + 7.0;
    CGFloat availH = slotAreaTop - slotAreaBottom;

    int cols = (slots <= 4) ? 2 : 3;
    int rows = (slots + cols - 1) / cols;
    CGFloat radius = 24.5;
    if (availH / rows < 53.0) {
        radius = MIN(23.0, (availH / rows) * 0.44);
    }
    CGFloat colStep = (box.size.width - 16.0) / cols;
    CGFloat rowStep = availH / rows;

    for (int i = 0; i < slots; i++) {
        int r = i / cols;
        int c = i % cols;
        CGFloat cx = box.origin.x + 8.0 + (c + 0.5) * colStep;
        CGFloat cy = slotAreaTop - (r + 0.5) * rowStep;
        NSString *hint = nil;
        if (i < [starters count]) {
            NSString *cid = starters[i];
            hint = charNames[cid] ?: cid;
        }
        drawTokenSlot(ctx, cx, cy, radius, accent, hint, i + 1);
    }
}

static void drawFullBoard(CGContextRef ctx, NSDictionary *cfg, CGFloat boardW, CGFloat boardH) {
    NSColor *ivory = colorFromHex(@"#F8F5EC", 1.0);
    NSColor *green = colorFromHex(@"#203D37", 1.0);
    NSColor *gold = colorFromHex(@"#A58958", 1.0);
    NSColor *muted = colorFromHex(@"#5A665E", 1.0);

    [ivory setFill];
    NSRectFill(NSMakeRect(0, 0, boardW, boardH));

    fillRoundRect(ctx, CGRectMake(14, 14, boardW - 28, boardH - 28), 10, nil, green, 1.5);
    fillRoundRect(ctx, CGRectMake(19, 19, boardW - 38, boardH - 38), 7, nil, gold, 0.7);

    fillRoundRect(ctx, CGRectMake(boardW * 0.47, 175, boardW * 0.50, 440), 18, colorFromHex(@"#E3EFF3", 0.55), colorFromHex(@"#1E6F7D", 0.25), 0.8);
    drawText(@"🌊 ზღვათა გზაჯვარედინი (საზღვაო ნაოსნობის ზონა)", 760, 520, 8.2, YES, colorFromHex(@"#1E6F7D", 0.75), @"center");

    CGRect topBanner = CGRectMake(26, boardH - 64, boardW - 52, 40);
    fillRoundRect(ctx, topBanner, 7, green, gold, 1.0);
    drawText(cfg[@"title"], 40, boardH - 41, 13.5, YES, colorFromHex(@"#F8F5EC", 1.0), @"left");
    drawText(cfg[@"subtitle"], 40, boardH - 55, 7.8, NO, colorFromHex(@"#E2D5B5", 1.0), @"left");
    drawText(@"━━ სახმელეთო გზა    ┈┈ საზღვაო გზა    ◯ 28 მმ ფიშკის სადგომი", boardW - 40, boardH - 47, 8.0, YES, colorFromHex(@"#FFD984", 1.0), @"right");

    NSDictionary *boxes = @{
        @"arabia":     [NSValue valueWithRect:NSMakeRect(28, 558, 270, 208)],
        @"wilderness": [NSValue valueWithRect:NSMakeRect(308, 438, 272, 220)],
        @"india":      [NSValue valueWithRect:NSMakeRect(28, 178, 270, 248)],
        @"khataveti":  [NSValue valueWithRect:NSMakeRect(610, 566, 265, 200)],
        @"mulgazanzar":[NSValue valueWithRect:NSMakeRect(890, 558, 272, 208)],
        @"gulansharo": [NSValue valueWithRect:NSMakeRect(610, 178, 272, 238)],
        @"kajeti":     [NSValue valueWithRect:NSMakeRect(896, 178, 266, 238)]
    };

    drawRouteCurve(ctx, CGPointMake(298, 665), CGPointMake(375, 658), CGPointMake(345, 705), NO);
    drawRouteCurve(ctx, CGPointMake(163, 426), CGPointMake(340, 438), CGPointMake(235, 472), NO);
    drawRouteCurve(ctx, CGPointMake(298, 395), CGPointMake(610, 680), CGPointMake(450, 725), NO);
    drawRouteCurve(ctx, CGPointMake(580, 548), CGPointMake(890, 610), CGPointMake(735, 535), NO);
    drawRouteCurve(ctx, CGPointMake(298, 195), CGPointMake(610, 195), CGPointMake(454, 165), YES);
    drawRouteCurve(ctx, CGPointMake(965, 558), CGPointMake(780, 416), CGPointMake(870, 485), YES);
    drawRouteCurve(ctx, CGPointMake(610, 405), CGPointMake(555, 438), CGPointMake(584, 425), YES);
    drawRouteCurve(ctx, CGPointMake(882, 305), CGPointMake(896, 305), CGPointMake(889, 325), NO);
    drawRouteCurve(ctx, CGPointMake(1035, 558), CGPointMake(1035, 416), CGPointMake(1065, 487), NO);

    NSMutableDictionary *charNames = [NSMutableDictionary dictionary];
    for (NSDictionary *ch in cfg[@"characters"]) {
        charNames[ch[@"id"]] = ch[@"short_name"];
    }

    for (NSDictionary *realm in cfg[@"realms"]) {
        NSValue *val = boxes[realm[@"id"]];
        if (val) {
            drawRealmBox(ctx, NSRectToCGRect([val rectValue]), realm, charNames);
        }
    }

    // Draw route pills in clean open corridors after boxes
    drawRoutePill(ctx, 378, 690, NO, @"არაბეთი ➔ ქვაბი (თ. 5, 36)");
    drawRoutePill(ctx, 212, 456, NO, @"ინდოეთი ➔ ქვაბი (თ. 25, 64)");
    drawRoutePill(ctx, 485, 725, NO, @"ინდოეთი ➔ ხატაეთი (თ. 17–19)");
    drawRoutePill(ctx, 688, 548, NO, @"ქვაბი ➔ მულღაზანზარი (თ. 26, 40, 54)");
    drawRoutePill(ctx, 444, 167, YES, @"ნესტანის კიდობნის ზღვის გზა (თ. 24, 45)");
    drawRoutePill(ctx, 795, 495, YES, @"საზღვაო გზა: ფრიდონი ➔ გულანშარო (თ. 41–42)");
    drawRoutePill(ctx, 680, 462, YES, @"ავთანდილის დაბრუნება წერილით (თ. 52–53)");
    drawRoutePill(ctx, 889, 434, NO, @"გულანშარო ➔ ქაჯეთი (თ. 47, 49)");
    drawRoutePill(ctx, 1068, 495, NO, @"სამი გმირის იერიში ქაჯეთს (თ. 55–57)");

    CGRect turnBox = CGRectMake(308, 178, 272, 238);
    fillRoundRect(ctx, turnBox, 9.0, colorFromHex(@"#FFFDF8", 0.96), gold, 1.4);
    CGRect turnHead = CGRectMake(311, 386, 266, 27);
    fillRoundRect(ctx, turnHead, 6.0, green, nil, 0);
    drawText(@"სვლის წესი და ფიშკების მოძრაობა", 444, 395, 9.2, YES, [NSColor whiteColor], @"center");

    NSArray *rules = @[
        @"1. თავის / ეტაპის გადაწევა: გადაადგილეთ მაჩვენებელი ქვედა სკალაზე (ეტაპი I–X ან თავი 1–65).",
        @"2. პერსონაჟთა გააქტიურება: დახედეთ A5 ბარათების უკანა მხარეს („თავებში“). ვინც მოცემულ თავში ჩანს, აქტიურდება.",
        @"3. გადაადგილება რუკაზე: გადაიყვანეთ გმირის 28 მმ ფიშკა სახმელეთო ან საზღვაო გზით შესაბამის სამეფოში.",
        @"4. წერილები და ნივთები: გადაეცით წერილის ან აბჯრის ფიშკა იმ გმირს, ვინც მას იმავე სამეფოში იღებს.",
        @"5. ქაჯეთის აღება და ქორწილები: შეკრიბეთ სამივე ძმადნაფიცი მულღაზანზარში, აიღეთ ქაჯეთი და დააბრუნეთ გმირები არაბეთსა და ინდოეთში!"
    ];
    CGFloat ry = 378.0;
    for (NSString *line in rules) {
        ry = drawWrappedText(line, 318, ry, 252, 6.7, 8.4, NO, green, @"left") - 3.2;
    }

    CGRect trackBox = CGRectMake(28, 26, boardW - 56, 138);
    fillRoundRect(ctx, trackBox, 8.0, colorFromHex(@"#FFFDF8", 0.98), green, 1.3);
    drawText(@"სიუჟეტის განვითარების სკალა — 10 საკვანძო ეტაპი და 65 თავი (შეესაბამება A5 ბარათების „თავებში“ სკალას)",
             boardW / 2.0, 148, 8.2, YES, green, @"center");

    NSArray *stages = cfg[@"chapter_stages"];
    for (int i = 0; i < 10; i++) {
        NSDictionary *st = stages[i];
        CGFloat panelOffset = (i < 5) ? 36.0 : 610.0;
        int localIdx = i % 5;
        CGFloat sw = 104.0;
        CGFloat sx = panelOffset + localIdx * (sw + 6.5);
        CGRect sRect = CGRectMake(sx, 78, sw, 62);
        fillRoundRect(ctx, sRect, 5.5, colorFromHex(@"#F8F5EC", 1.0), gold, 0.9);
        CGRect sTop = CGRectMake(sx, 123, sw, 17);
        fillRoundRect(ctx, sTop, 4.5, green, nil, 0);
        drawText([NSString stringWithFormat:@"ეტაპი %@ • თ. %@", st[@"stage"], st[@"chapters"]],
                 sx + sw / 2.0, 128, 6.5, YES, [NSColor whiteColor], @"center");
        drawWrappedText(st[@"title"], sx + 4, 119, sw - 8, 6.6, 7.8, YES, green, @"center");
        drawWrappedText(st[@"realms"], sx + 4, 98, sw - 8, 5.8, 7.0, NO, muted, @"center");
    }

    drawText(@"თავები 1–32:", 36, 56, 7.0, YES, green, @"left");
    drawText(@"თავები 33–65:", 610, 56, 7.0, YES, green, @"left");
    for (int ch = 1; ch <= 65; ch++) {
        CGFloat cx;
        if (ch <= 32) {
            cx = 105.0 + (ch - 1) * 14.8;
        } else {
            cx = 682.0 + (ch - 33) * 14.6;
        }
        CGFloat cy = 58.0;
        BOOL major = (ch == 1 || ch == 65 || ch % 5 == 0);
        CGFloat rad = major ? 5.6 : 4.4;
        NSColor *cFill = major ? colorFromHex(@"#203D37", 1.0) : colorFromHex(@"#F8F5EC", 1.0);
        NSColor *cText = major ? [NSColor whiteColor] : green;
        fillRoundRect(ctx, CGRectMake(cx - rad, cy - rad, rad * 2, rad * 2), rad, cFill, green, 0.7);
        drawText([NSString stringWithFormat:@"%d", ch], cx, cy - 2.3, major ? 5.4 : 4.7, major, cText, @"center");
        if (major) {
            drawText([NSString stringWithFormat:@"თ.%d", ch], cx, cy - 15.0, 5.2, YES, muted, @"center");
        }
    }
}

static void drawCharacterToken(CGContextRef ctx, CGFloat cx, CGFloat cy, CGFloat radius, NSDictionary *ch) {
    NSColor *realmColor = colorFromHex(ch[@"color"], 1.0);
    NSColor *gold = colorFromHex(@"#A58958", 1.0);
    NSColor *ivory = colorFromHex(@"#F8F5EC", 1.0);
    NSColor *green = colorFromHex(@"#203D37", 1.0);

    CGContextSaveGState(ctx);
    NSBezierPath *cutRing = [NSBezierPath bezierPathWithOvalInRect:NSMakeRect(cx - radius - 2, cy - radius - 2, (radius + 2) * 2, (radius + 2) * 2)];
    [colorFromHex(@"#9AA39C", 0.75) setStroke];
    CGFloat dash[2] = {3.0, 3.0};
    [cutRing setLineDash:dash count:2 phase:0];
    [cutRing setLineWidth:0.5];
    [cutRing stroke];

    fillRoundRect(ctx, CGRectMake(cx - radius, cy - radius, radius * 2, radius * 2), radius, realmColor, gold, 1.4);
    fillRoundRect(ctx, CGRectMake(cx - radius + 4.5, cy - radius + 4.5, (radius - 4.5) * 2, (radius - 4.5) * 2), radius - 4.5, ivory, gold, 0.9);

    CGFloat imgRad = radius - 6.5;
    NSImage *img = downsampledPortrait(ch[@"asset"], 360);
    if (img) {
        CGContextSaveGState(ctx);
        NSBezierPath *clip = [NSBezierPath bezierPathWithOvalInRect:NSMakeRect(cx - imgRad, cy - imgRad + 3.0, imgRad * 2, imgRad * 2)];
        [clip addClip];
        [img drawInRect:NSMakeRect(cx - imgRad, cy - imgRad + 3.0, imgRad * 2, imgRad * 2)
               fromRect:NSZeroRect
              operation:NSCompositingOperationSourceOver
               fraction:1.0];
        CGContextRestoreGState(ctx);
    }

    CGRect banner = CGRectMake(cx - radius + 3.0, cy - radius + 4.0, (radius - 3.0) * 2, 16.5);
    fillRoundRect(ctx, banner, 5.0, green, gold, 0.8);
    NSString *shortName = ch[@"short_name"];
    CGFloat fontSize = ([shortName length] > 11) ? 5.6 : 6.4;
    drawText(shortName, cx, cy - radius + 12.2, fontSize, YES, [NSColor whiteColor], @"center");
    drawText(ch[@"realm_short"], cx, cy - radius + 6.0, 5.0, NO, colorFromHex(@"#FFD984", 1.0), @"center");
    CGContextRestoreGState(ctx);
}

static void drawSymbolicToken(CGContextRef ctx, CGFloat cx, CGFloat cy, CGFloat radius, NSDictionary *tok, NSString *categoryLabel) {
    NSColor *accent = colorFromHex(tok[@"color"], 1.0);
    NSColor *gold = colorFromHex(@"#A58958", 1.0);
    NSColor *ivory = colorFromHex(@"#F8F5EC", 1.0);
    NSColor *green = colorFromHex(@"#203D37", 1.0);

    NSBezierPath *cutRing = [NSBezierPath bezierPathWithOvalInRect:NSMakeRect(cx - radius - 2, cy - radius - 2, (radius + 2) * 2, (radius + 2) * 2)];
    [colorFromHex(@"#9AA39C", 0.75) setStroke];
    CGFloat dash[2] = {3.0, 3.0};
    [cutRing setLineDash:dash count:2 phase:0];
    [cutRing setLineWidth:0.5];
    [cutRing stroke];

    fillRoundRect(ctx, CGRectMake(cx - radius, cy - radius, radius * 2, radius * 2), radius, accent, gold, 1.4);
    fillRoundRect(ctx, CGRectMake(cx - radius + 4.5, cy - radius + 4.5, (radius - 4.5) * 2, (radius - 4.5) * 2), radius - 4.5, ivory, gold, 0.9);

    drawText(categoryLabel, cx, cy + radius - 18.0, 4.6, YES, accent, @"center");
    fillRoundRect(ctx, CGRectMake(cx - 15, cy + 1.0, 30, 15.5), 5.5, accent, gold, 0.8);
    drawText(tok[@"code"], cx, cy + 5.2, 7.8, YES, [NSColor whiteColor], @"center");
    drawWrappedText(tok[@"name"], cx - radius + 7.5, cy - 2.0, (radius - 7.5) * 2, 5.8, 6.7, YES, green, @"center");
    drawText(tok[@"subtitle"], cx, cy - radius + 14.0, 4.6, NO, colorFromHex(@"#55625A", 1.0), @"center");
}

static void drawTokensPage1(CGContextRef ctx, NSDictionary *cfg, CGFloat pw, CGFloat ph) {
    NSColor *ivory = colorFromHex(@"#F8F5EC", 1.0);
    NSColor *green = colorFromHex(@"#203D37", 1.0);
    NSColor *gold = colorFromHex(@"#A58958", 1.0);
    NSColor *muted = colorFromHex(@"#5A665E", 1.0);

    [ivory setFill];
    NSRectFill(NSMakeRect(0, 0, pw, ph));
    fillRoundRect(ctx, CGRectMake(18, 18, pw - 36, ph - 36), 8, nil, green, 1.2);

    drawText(@"ვეფხისტყაოსანი — პერსონაჟთა სათამაშო ფიშკები (21 გმირი • Ø 28 მმ)", 32, ph - 42, 12.6, YES, green, @"left");
    drawText(@"ამობეჭდეთ 100%-იანი ზომით A4 ფურცელზე და გამოჭერით წყვეტილ ხაზზე. ფერადი რკალი აღნიშნავს პერსონაჟის მშობლიურ სამეფოს.",
             32, ph - 57, 7.4, NO, muted, @"left");
    fillRoundRect(ctx, CGRectMake(32, ph - 63, pw - 64, 1.0), 0.5, gold, nil, 0);

    NSArray *chars = cfg[@"characters"];
    NSArray *trackers = cfg[@"tracker_tokens"];
    CGFloat radius = 14.0 * (72.0 / 25.4);
    int cols = 4;
    CGFloat startX = 82.0, stepX = (pw - 164.0) / (cols - 1);
    CGFloat startY = ph - 122.0, stepY = 114.0;

    for (int i = 0; i < 24; i++) {
        int r = i / cols;
        int c = i % cols;
        CGFloat cx = startX + c * stepX;
        CGFloat cy = startY - r * stepY;
        if (i < [chars count]) {
            NSDictionary *ch = chars[i];
            drawCharacterToken(ctx, cx, cy, radius, ch);
            drawText([NSString stringWithFormat:@"%02d. %@", i + 1, ch[@"name"]], cx, cy - radius - 11.0, 6.4, YES, green, @"center");
            drawText([NSString stringWithFormat:@"%@ (%@ თავი)", ch[@"realm_name"], ch[@"chapters_count"]], cx, cy - radius - 19.5, 5.5, NO, muted, @"center");
        } else {
            NSDictionary *tr = trackers[i - [chars count]];
            drawSymbolicToken(ctx, cx, cy, radius, tr, @"მაჩვენებელი");
            drawText(tr[@"name"], cx, cy - radius - 11.0, 6.4, YES, green, @"center");
            drawText(tr[@"subtitle"], cx, cy - radius - 19.5, 5.5, NO, muted, @"center");
        }
    }

    drawText(@"ფურცელი 1 / 3 • პერსონაჟთა ფიშკები (Ø 28 მმ) • ვეფხისტყაოსნის სამაგიდო გამოცემა", pw / 2.0, 28, 7.4, NO, muted, @"center");
}

static void drawTokensPage2(CGContextRef ctx, NSDictionary *cfg, CGFloat pw, CGFloat ph) {
    NSColor *ivory = colorFromHex(@"#F8F5EC", 1.0);
    NSColor *green = colorFromHex(@"#203D37", 1.0);
    NSColor *gold = colorFromHex(@"#A58958", 1.0);
    NSColor *muted = colorFromHex(@"#5A665E", 1.0);

    [ivory setFill];
    NSRectFill(NSMakeRect(0, 0, pw, ph));
    fillRoundRect(ctx, CGRectMake(18, 18, pw - 36, ph - 36), 8, nil, green, 1.2);

    drawText(@"ვეფხისტყაოსანი — წერილების, ნივთებისა და ურთიერთობების ფიშკები", 32, ph - 42, 12.6, YES, green, @"left");
    drawText(@"სათამაშო ატრიბუტიკა: გადაადგილეთ წერილები და რელიკვიები გმირებთან ერთად, ხოლო ურთიერთობის ჟეტონებით აღნიშნეთ კავშირები.",
             32, ph - 57, 7.4, NO, muted, @"left");
    fillRoundRect(ctx, CGRectMake(32, ph - 63, pw - 64, 1.0), 0.5, gold, nil, 0);

    CGFloat radius = 14.0 * (72.0 / 25.4);
    int cols = 4;
    CGFloat startX = 82.0, stepX = (pw - 164.0) / (cols - 1);

    drawText(@"I. საკვანძო წერილები და საჭურველი (8 ფიშკა — გადადის პერსონაჟიდან პერსონაჟზე)", 32, ph - 82, 9.0, YES, green, @"left");
    NSArray *items = cfg[@"item_tokens"];
    for (int i = 0; i < [items count]; i++) {
        int r = i / cols;
        int c = i % cols;
        CGFloat cx = startX + c * stepX;
        CGFloat cy = (ph - 138.0) - r * 114.0;
        NSDictionary *it = items[i];
        drawSymbolicToken(ctx, cx, cy, radius, it, @"ნივთი / წერილი");
        drawText(it[@"name"], cx, cy - radius - 10.5, 6.3, YES, green, @"center");
        drawText(it[@"subtitle"], cx, cy - radius - 18.5, 5.4, NO, muted, @"center");
    }

    drawText(@"II. ურთიერთობის 8 ტიპის ჟეტონი (დადეთ პერსონაჟთა ბარათებს შორის კავშირის გასახსნელად)", 32, ph - 322, 9.0, YES, green, @"left");
    NSArray *bonds = cfg[@"bond_tokens"];
    for (int i = 0; i < [bonds count]; i++) {
        int r = i / cols;
        int c = i % cols;
        CGFloat cx = startX + c * stepX;
        CGFloat cy = (ph - 378.0) - r * 112.0;
        NSDictionary *bd = bonds[i];
        drawSymbolicToken(ctx, cx, cy, radius, bd, @"ურთიერთობა");
        drawText(bd[@"name"], cx, cy - radius - 10.5, 6.3, YES, green, @"center");
        drawText(bd[@"subtitle"], cx, cy - radius - 18.5, 5.4, NO, muted, @"center");
    }

    drawText(@"III. დამატებითი სვლის მაჩვენებლები და ნივთების დანიშნულება", 32, ph - 558, 9.0, YES, green, @"left");
    NSArray *trackers = cfg[@"tracker_tokens"];
    for (int i = 2; i < 6; i++) {
        int c = i - 2;
        CGFloat cx = startX + c * stepX;
        CGFloat cy = ph - 614.0;
        NSDictionary *tr = trackers[i];
        drawSymbolicToken(ctx, cx, cy, radius, tr, @"სვლა / გზა");
        drawText(tr[@"name"], cx, cy - radius - 10.5, 6.3, YES, green, @"center");
        drawText(tr[@"subtitle"], cx, cy - radius - 18.5, 5.4, NO, muted, @"center");
    }

    CGRect refBox = CGRectMake(32, 44, pw - 64, 108);
    fillRoundRect(ctx, refBox, 6.0, colorFromHex(@"#FFFDF8", 1.0), gold, 0.9);
    CGFloat ty = 142.0;
    for (int i = 0; i < [items count]; i++) {
        NSDictionary *it = items[i];
        CGFloat colX = (i < 4) ? 42.0 : (pw / 2.0 + 8.0);
        CGFloat rowY = (i % 4) * 24.0;
        NSString *line = [NSString stringWithFormat:@"• %@: %@", it[@"name"], it[@"description"]];
        drawWrappedText(line, colX, ty - rowY, (pw - 100) / 2.0, 6.1, 7.4, NO, green, @"left");
    }

    drawText(@"ფურცელი 2 / 3 • ნივთებისა და ურთიერთობების ფიშკები (Ø 28 მმ) • ვეფხისტყაოსნის სამაგიდო გამოცემა", pw / 2.0, 28, 7.4, NO, muted, @"center");
}

static void drawRulesPage(CGContextRef ctx, NSDictionary *cfg, CGFloat pw, CGFloat ph) {
    NSColor *ivory = colorFromHex(@"#F8F5EC", 1.0);
    NSColor *green = colorFromHex(@"#203D37", 1.0);
    NSColor *gold = colorFromHex(@"#A58958", 1.0);
    NSColor *muted = colorFromHex(@"#5A665E", 1.0);

    [ivory setFill];
    NSRectFill(NSMakeRect(0, 0, pw, ph));
    fillRoundRect(ctx, CGRectMake(18, 18, pw - 36, ph - 36), 8, nil, green, 1.2);

    CGRect banner = CGRectMake(32, ph - 82, pw - 64, 52);
    fillRoundRect(ctx, banner, 7, green, gold, 1.0);
    drawText(@"ვეფხისტყაოსანი — სამაგიდო თამაშის წესები და კომპონენტების გზამკვლევი", 46, ph - 52, 12.6, YES, [NSColor whiteColor], @"left");
    drawText(@"როგორ დავაკავშიროთ A5 პერსონაჟთა ბარათები, 7 სამეფოს რუკა და 28 მმ მოძრავი ფიშკები", 46, ph - 69, 7.8, NO, colorFromHex(@"#FFD984", 1.0), @"left");

    NSArray *sections = @[
        @{
            @"title": @"1. სამაგიდო კომპლექტის შემადგენლობა (ატრიბუტიკა)",
            @"body": @"• 21 პერსონაჟის A5 ბარათი (148 × 210 მმ): იდება მაგიდაზე მოთამაშეთა წინ. წინა მხარეს მოცემულია პორტრეტი, სამეფო და როლი, ხოლო უკანა მხარეს — სიუჟეტი, გააზრება, ურთიერთობების გალერეა და 65 თავის სკალა („თავებში“).\n"
                     @"• 7 სამეფოს სათამაშო რუკა-დაფა (A3 ან 2×A4): ასახავს პოემის შვიდივე სამეფოს (არაბეთი, უდაბნო/ქვაბი, ინდოეთი, ხატაეთი, მულღაზანზარი, გულანშარო, ქაჯეთი), სახმელეთო/საზღვაო გზებსა და ქვედა 65-თავიან სკალას.\n"
                     @"• 21 პერსონაჟის ფიშკა + 22 ნივთის, ურთიერთობისა და სვლის ფიშკა (Ø 28 მმ): მხოლოდ ეს მცირე დისკები მოძრაობს უშუალოდ რუკის სამეფოებსა და სადგომებზე."
        },
        @{
            @"title": @"2. საწყისი განლაგება მაგიდაზე (Setup)",
            @"body": @"• გაშალეთ 7 სამეფოს რუკა მაგიდის ცენტრში (ორ A4 ფურცელზე ბეჭდვისას შეაერთეთ მარცხენა და მარჯვენა ნახევარი).\n"
                     @"• დაალაგეთ პერსონაჟთა 28 მმ ფიშკები თავიანთ მშობლიურ სამეფოებში (რუკის სადგომებზე მითითებულია საწყისი გმირები: არაბეთში — როსტევანი, თინათინი, ავთანდილი, შერმადინი, სოგრატი; ქვაბში — ტარიელი და ასმათი; ინდოეთში — ფარსადანი, სარიდანი, ნესტანი, დავარი, ხვარაზმშას ძე; ხატაეთში — რამაზი; მულღაზანზარში — ფრიდონი; გულანშაროში — ფატმანი, უსენი, ჭაშნაგირი, სურხავი; ქაჯეთში — დულარდუხტი და როსანი).\n"
                     @"• დადეთ „თავის მაჩვენებელი“ თავი 1-ზე, ხოლო „ეტაპის მაჩვენებელი“ — ეტაპ I-ზე."
        },
        @{
            @"title": @"3. როგორ მოძრაობენ ფიშკები თამაშის განვითარებისას",
            @"body": @"• ყოველ რაუნდში მოთამაშეები გადაწევენ თავის/ეტაპის მაჩვენებელს და ამოწმებენ A5 ბარათების ქვედა სკალას („თავებში“): მუქი წრე ნიშნავს, რომ პერსონაჟი მოცემულ თავში მოქმედებს.\n"
                     @"• აქტიური პერსონაჟები ასრულებენ მოქმედებებს (რაუნდში 2 ან 3 მოქმედება, აღინიშნება ფიშკებით I, II, III):\n"
                     @"  1) მგზავრობა სამეფოებს შორის: გადაიყვანეთ გმირის ფიშკა მეზობელ სამეფოში სახმელეთო (მუქი ხაზი) ან საზღვაო (წყვეტილი ხაზი) გზით.\n"
                     @"  2) შეხვედრა და ურთიერთობა: როცა ორი პერსონაჟის ფიშკა ერთსა და იმავე სამეფოშია და მათ A5 ბარათების „ურთიერთობებში“ ერთმანეთი ჰყავთ, გახსენით შესაბამისი ურთიერთობის ჟეტონი (მაგ. დაძმობილება, მიჯნურობა, ეპისტოლე, ბრძოლა).\n"
                     @"  3) წერილის ან საჭურვლის გადაცემა: წერილის ფიშკა (ანდერძი, ფატმანის წერილი, ნესტანის წერილი, ცნობა ფრიდონთან) და დევთა სამი აბჯარი მოძრაობს მატარებელ გმირთან ან „ხომალდი/მაცნე“ ფიშკასთან ერთად."
        },
        @{
            @"title": @"4. მოგების პირობა და 3 სათამაშო რეჟიმი",
            @"body": @"• კოოპერატიული თავგადასავალი (მთელი პოემა 10 ეტაპად): გაიარეთ ათივე ეტაპი — მოძებნეთ ტარიელი ქვაბში, გულანშაროში ფატმანის დახმარებით გაიგეთ ნესტანის სამყოფელი, მიუტანეთ წერილი ტარიელს, გამოიტანეთ ქვაბიდან დევთა სამი აბჯარი, შეკრიბეთ ტარიელი, ავთანდილი და ფრიდონი მულღაზანზარში, ერთდროულად დაიკავეთ ქაჯეთის 3 კარიბჭე ნესტანის გამოსახსნელად და დაასრულეთ თამაში არაბეთსა და ინდოეთში ქორწილებით!\n"
                     @"• სცენარული რეჟიმი (ცალკეული ეპიზოდები): ითამაშეთ კონკრეტული თავები (მაგ. თავები 52–54: „წერილი და შეყრა“) მხოლოდ მონაწილე გმირების A5 ბარათებითა და ფიშკებით.\n"
                     @"• სასწავლო-კვლევითი რეჟიმი: წაიკითხეთ თავი, იპოვეთ A5 ბარათების 65-თავიან სკალაზე ყველა მონაწილე პერსონაჟი და გადაადგილეთ მათი ფიშკები რუკაზე."
        }
    ];

    CGFloat y = ph - 98.0;
    for (NSDictionary *sec in sections) {
        fillRoundRect(ctx, CGRectMake(32, y - 22, pw - 64, 20), 4.0, colorFromHex(@"#EFE9D8", 1.0), gold, 0.7);
        drawText(sec[@"title"], 42, y - 16, 9.2, YES, green, @"left");
        y = drawWrappedText(sec[@"body"], 40, y - 28, pw - 80, 7.8, 11.0, NO, colorFromHex(@"#202A24", 1.0), @"left") - 14.0;
    }

    drawText(@"ფურცელი 3 / 3 • თამაშის წესები და გზამკვლევი • ვეფხისტყაოსნის სამაგიდო გამოცემა", pw / 2.0, 28, 7.4, NO, muted, @"center");
}

static void savePDFPageAsPNG(CGPDFDocumentRef doc, int pageNumber, NSString *outPath, CGFloat scale) {
    CGPDFPageRef page = CGPDFDocumentGetPage(doc, pageNumber);
    if (!page) return;
    CGRect box = CGPDFPageGetBoxRect(page, kCGPDFMediaBox);
    int w = (int)round(box.size.width * scale);
    int h = (int)round(box.size.height * scale);
    NSBitmapImageRep *rep = [[NSBitmapImageRep alloc]
        initWithBitmapDataPlanes:NULL
                      pixelsWide:w
                      pixelsHigh:h
                   bitsPerSample:8
                 samplesPerPixel:4
                        hasAlpha:YES
                        isPlanar:NO
                  colorSpaceName:NSDeviceRGBColorSpace
                     bytesPerRow:0
                    bitsPerPixel:0];
    NSGraphicsContext *nsCtx = [NSGraphicsContext graphicsContextWithBitmapImageRep:rep];
    [NSGraphicsContext saveGraphicsState];
    [NSGraphicsContext setCurrentContext:nsCtx];
    CGContextRef ctx = [nsCtx CGContext];
    CGContextSetRGBFillColor(ctx, 1, 1, 1, 1);
    CGContextFillRect(ctx, CGRectMake(0, 0, w, h));
    CGContextScaleCTM(ctx, scale, scale);
    CGContextDrawPDFPage(ctx, page);
    [NSGraphicsContext restoreGraphicsState];
    NSData *png = [rep representationUsingType:NSBitmapImageFileTypePNG properties:@{}];
    [png writeToFile:outPath atomically:YES];
}

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSString *cfgPath = [NSString stringWithUTF8String:argv[1]];
        NSDictionary *cfg = [NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfFile:cfgPath] options:0 error:nil];
        for (NSString *fp in cfg[@"fonts"]) {
            registerFont(fp);
        }

        CGFloat mm = 72.0 / 25.4;
        CGFloat a3w = 420.0 * mm, a3h = 297.0 * mm;
        CGFloat a4w = 210.0 * mm, a4h = 297.0 * mm;

        // 1. A3 Full Landscape Board
        {
            NSURL *url = [NSURL fileURLWithPath:cfg[@"out_a3_map"]];
            CGRect box = CGRectMake(0, 0, a3w, a3h);
            CGContextRef pdf = CGPDFContextCreateWithURL((__bridge CFURLRef)url, &box, NULL);
            CGPDFContextBeginPage(pdf, NULL);
            NSGraphicsContext *nsCtx = [NSGraphicsContext graphicsContextWithCGContext:pdf flipped:NO];
            [NSGraphicsContext saveGraphicsState];
            [NSGraphicsContext setCurrentContext:nsCtx];
            drawFullBoard(pdf, cfg, a3w, a3h);
            [NSGraphicsContext restoreGraphicsState];
            CGPDFContextEndPage(pdf);
            CGPDFContextClose(pdf);
            CGContextRelease(pdf);
        }

        // 2. 2x A4 Split Map PDF (Left A4 + Right A4)
        {
            NSURL *url = [NSURL fileURLWithPath:cfg[@"out_a4_split_map"]];
            CGRect box = CGRectMake(0, 0, a4w, a4h);
            CGContextRef pdf = CGPDFContextCreateWithURL((__bridge CFURLRef)url, &box, NULL);
            for (int half = 0; half < 2; half++) {
                CGPDFContextBeginPage(pdf, NULL);
                NSGraphicsContext *nsCtx = [NSGraphicsContext graphicsContextWithCGContext:pdf flipped:NO];
                [NSGraphicsContext saveGraphicsState];
                [NSGraphicsContext setCurrentContext:nsCtx];
                CGContextSaveGState(pdf);
                if (half == 1) {
                    CGContextTranslateCTM(pdf, -a4w, 0);
                }
                drawFullBoard(pdf, cfg, a3w, a3h);
                CGContextRestoreGState(pdf);

                NSColor *muted = colorFromHex(@"#647168", 0.85);
                if (half == 0) {
                    drawText(@"▶ შეაერთეთ მარჯვენა ნახევართან (ფურცელი 2/2)", a4w - 18, 5, 6.2, YES, muted, @"right");
                } else {
                    drawText(@"◀ შეაერთეთ მარცხენა ნახევართან (ფურცელი 1/2)", 18, 5, 6.2, YES, muted, @"left");
                }
                [NSGraphicsContext restoreGraphicsState];
                CGPDFContextEndPage(pdf);
            }
            CGPDFContextClose(pdf);
            CGContextRelease(pdf);
        }

        // 3. 3-Page A4 Tokens & Rules PDF
        {
            NSURL *url = [NSURL fileURLWithPath:cfg[@"out_tokens_pdf"]];
            CGRect box = CGRectMake(0, 0, a4w, a4h);
            CGContextRef pdf = CGPDFContextCreateWithURL((__bridge CFURLRef)url, &box, NULL);

            for (int p = 1; p <= 3; p++) {
                CGPDFContextBeginPage(pdf, NULL);
                NSGraphicsContext *nsCtx = [NSGraphicsContext graphicsContextWithCGContext:pdf flipped:NO];
                [NSGraphicsContext saveGraphicsState];
                [NSGraphicsContext setCurrentContext:nsCtx];
                if (p == 1) drawTokensPage1(pdf, cfg, a4w, a4h);
                else if (p == 2) drawTokensPage2(pdf, cfg, a4w, a4h);
                else drawRulesPage(pdf, cfg, a4w, a4h);
                [NSGraphicsContext restoreGraphicsState];
                CGPDFContextEndPage(pdf);
            }
            CGPDFContextClose(pdf);
            CGContextRelease(pdf);
        }

        // 4. 5-Page Complete A4 Packet (2 Map Panels + 2 Token Sheets + 1 Rules Sheet)
        {
            PDFDocument *complete = [[PDFDocument alloc] init];
            PDFDocument *splitMap = [[PDFDocument alloc] initWithURL:[NSURL fileURLWithPath:cfg[@"out_a4_split_map"]]];
            PDFDocument *tokensDoc = [[PDFDocument alloc] initWithURL:[NSURL fileURLWithPath:cfg[@"out_tokens_pdf"]]];
            for (NSUInteger i = 0; i < [splitMap pageCount]; i++) {
                [complete insertPage:[splitMap pageAtIndex:i] atIndex:[complete pageCount]];
            }
            for (NSUInteger i = 0; i < [tokensDoc pageCount]; i++) {
                [complete insertPage:[tokensDoc pageAtIndex:i] atIndex:[complete pageCount]];
            }
            [complete writeToFile:cfg[@"out_complete_a4"]];
        }

        // 5. Render PNG Previews for visual QA
        {
            CGPDFDocumentRef a3Doc = CGPDFDocumentCreateWithURL((__bridge CFURLRef)[NSURL fileURLWithPath:cfg[@"out_a3_map"]]);
            savePDFPageAsPNG(a3Doc, 1, cfg[@"preview_a3_map"], 1.4);
            CGPDFDocumentRelease(a3Doc);

            CGPDFDocumentRef tokDoc = CGPDFDocumentCreateWithURL((__bridge CFURLRef)[NSURL fileURLWithPath:cfg[@"out_tokens_pdf"]]);
            savePDFPageAsPNG(tokDoc, 1, cfg[@"preview_tokens_1"], 1.5);
            savePDFPageAsPNG(tokDoc, 2, cfg[@"preview_tokens_2"], 1.5);
            savePDFPageAsPNG(tokDoc, 3, cfg[@"preview_rules"], 1.5);
            CGPDFDocumentRelease(tokDoc);
        }
    }
    return 0;
}
"""


def main():
    font_dir = ROOT / "tmp" / "georgian-deck" / "fonts"
    fonts = [
        str(font_dir / f)
        for f in ("Georgian-Regular.ttf", "Georgian-Bold.ttf", "Georgian-Display.ttf")
        if (font_dir / f).exists()
    ]

    out_a3_map = OUT / "pantersskin-realm-map-ka-a3.pdf"
    out_a4_split_map = OUT / "pantersskin-realm-map-ka-a4-split.pdf"
    out_tokens_pdf = OUT / "pantersskin-tokens-and-guide-ka-a4.pdf"
    out_complete_a4 = OUT / "pantersskin-board-game-complete-ka-a4.pdf"

    cfg = {
        **BOARD_DATA,
        "fonts": fonts,
        "characters": PAINTED_CHARACTERS,
        "out_a3_map": str(out_a3_map),
        "out_a4_split_map": str(out_a4_split_map),
        "out_tokens_pdf": str(out_tokens_pdf),
        "out_complete_a4": str(out_complete_a4),
        "preview_a3_map": str(OUT / "preview-realm-map-a3.png"),
        "preview_tokens_1": str(OUT / "preview-character-tokens.png"),
        "preview_tokens_2": str(OUT / "preview-item-and-bond-tokens.png"),
        "preview_rules": str(OUT / "preview-rules.png"),
    }

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cfg_file = tmp_path / "cfg.json"
        bin_file = tmp_path / "build_realm_board"
        cfg_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
        subprocess.run(
            [
                "clang", "-x", "objective-c", "-O2",
                "-framework", "Foundation",
                "-framework", "AppKit",
                "-framework", "PDFKit",
                "-framework", "CoreText",
                "-", "-o", str(bin_file),
            ],
            input=OBJC_BUILDER.encode("utf-8"),
            check=True,
        )
        subprocess.run([str(bin_file), str(cfg_file)], check=True)

    manifest = {
        "date": "2026-11-08",
        "language": "ka",
        "character_tokens_count": len(PAINTED_CHARACTERS),
        "item_tokens_count": len(BOARD_DATA["item_tokens"]),
        "bond_tokens_count": len(BOARD_DATA["bond_tokens"]),
        "tracker_tokens_count": len(BOARD_DATA["tracker_tokens"]),
        "token_diameter_mm": 28,
        "realms_count": len(BOARD_DATA["realms"]),
        "outputs": [
            {"file": str(out_a3_map.relative_to(ROOT)), "pages": 1, "format": "A3 landscape (420x297 mm)"},
            {"file": str(out_a4_split_map.relative_to(ROOT)), "pages": 2, "format": "2x A4 portrait side-by-side (joins to A3 420x297 mm)"},
            {"file": str(out_tokens_pdf.relative_to(ROOT)), "pages": 3, "format": "A4 portrait (Page 1: 21 Character Tokens + 3 Trackers, Page 2: 8 Item/Epistle + 8 Bond + 4 Action Tokens, Page 3: Rules)"},
            {"file": str(out_complete_a4.relative_to(ROOT)), "pages": 5, "format": "Complete A4 Print Packet (2 Map Sheets + 2 Token Sheets + 1 Rules Sheet)"}
        ]
    }
    (OUT / "build-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    for p in (out_a3_map, out_a4_split_map, out_tokens_pdf, out_complete_a4):
        print(f"{p.relative_to(ROOT)} ({p.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
