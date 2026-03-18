"""Onboard form HTML — shown after Slack OAuth callback."""
from __future__ import annotations


def render_onboard_form(team_id: str, team_name: str, bot_token: str) -> str:
    """Return HTML for the post-install configuration form."""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Kolay IK — Setup for {team_name}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .card {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            max-width: 480px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .logo {{ font-size: 48px; text-align: center; margin-bottom: 8px; }}
        h2 {{ text-align: center; color: #1a1a2e; margin-bottom: 4px; font-size: 22px; }}
        .subtitle {{ text-align: center; color: #666; font-size: 14px; margin-bottom: 28px; }}
        label {{ display: block; font-weight: 600; margin-bottom: 6px; color: #333; font-size: 14px; }}
        input[type="text"], input[type="password"] {{
            width: 100%;
            padding: 10px 14px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            margin-bottom: 18px;
            transition: border-color 0.2s;
        }}
        input:focus {{ border-color: #667eea; outline: none; }}
        .hint {{ font-size: 12px; color: #888; margin-top: -14px; margin-bottom: 16px; }}
        button {{
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s;
        }}
        button:hover {{ transform: scale(1.02); }}
        button:active {{ transform: scale(0.98); }}
        .badge {{
            display: inline-block;
            background: #e8f5e9;
            color: #2e7d32;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 13px;
            font-weight: 500;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">K</div>
        <h2>Connect Kolay IK</h2>
        <p class="subtitle">
            <span class="badge">✓ {team_name}</span> workspace connected
        </p>

        <form method="POST" action="complete">
            <input type="hidden" name="team_id" value="{team_id}" />
            <input type="hidden" name="team_name" value="{team_name}" />
            <input type="hidden" name="bot_token" value="{bot_token}" />

            <label for="kolay_api_token">Kolay API Token</label>
            <input type="password" id="kolay_api_token" name="kolay_api_token"
                   placeholder="Paste your Kolay IK API token" required />
            <p class="hint">Found in Kolay IK → Settings → API</p>

            <label for="allowed_channels">Allowed Channels <span style="font-weight:normal;color:#888">(optional)</span></label>
            <input type="text" id="allowed_channels" name="allowed_channels"
                   placeholder="C0123ABC, C0456DEF" />
            <p class="hint">Comma-separated Slack channel IDs. Leave empty = all channels.</p>

            <label for="allowed_users">Allowed Users <span style="font-weight:normal;color:#888">(optional)</span></label>
            <input type="text" id="allowed_users" name="allowed_users"
                   placeholder="U0123456, U0654321" />
            <p class="hint">Comma-separated Slack user IDs. Leave empty = all users.</p>

            <button type="submit">Save &amp; Activate</button>
        </form>
    </div>
</body>
</html>
"""
