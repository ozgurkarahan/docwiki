"""WebVTT transcript of the toolbox talk on cold-weather start-up (2025-11-12)."""

from __future__ import annotations

from .common import STAMP
from .world import World

# (start, end, speaker or None, text) - times in seconds from the start of the recording.
_CUES: list[tuple[float, float, str | None, str]] = [
    (0.0, 4.0, None, STAMP),
    (4.5, 11.0, "Dario Penwarden", "Morning everyone. Today's toolbox talk is about cold-weather "
     "start-up, now that most gearboxes run on the new oil."),
    (11.5, 19.0, "Dario Penwarden", "Quick status of the conversion to PWG 220: nine turbines are "
     "done, WTG-11 is being converted today and WTG-12 next Wednesday."),
    (19.5, 27.0, "Dario Penwarden", "WTG-09 is planned for the twenty-fourth, if the access road "
     "stays open."),
    (27.5, 37.0, "Dario Penwarden", "The important change: with PWG 220 the minimum oil "
     "temperature for start-up is plus five degrees. With the old PWG 320 it was plus ten."),
    (37.5, 45.0, "Callum Rydings", "So the turbines will be back in production faster after a "
     "cold night?"),
    (45.5, 56.0, "Dario Penwarden", "Yes. From minus twenty the heaters need about four hours to "
     "bring the sump to plus five. Last January WTG-02 and WTG-09 needed more than six hours."),
    (56.5, 65.0, "Dario Penwarden", "Never bypass the start inhibit. The controller waits for the "
     "oil temperature for a reason."),
    (65.5, 75.0, "\u00c9lise Ternaux", "And if WTG-09 still has PWG 320 in January, which "
     "temperature applies?"),
    (75.5, 83.0, "Dario Penwarden", "Then its start temperature stays at plus ten until the "
     "conversion is done. The parameter is changed only with the new oil."),
    (83.5, 94.0, "Dario Penwarden", "If you see A2120, gearbox oil pressure low, right after a "
     "cold start, give the heaters more time before you call me. It is usually cold oil, not a "
     "pump fault."),
    (94.5, 103.0, "Callum Rydings", "What about the filter alarm, A2140? We had that on WTG-05 "
     "last winter."),
    (103.5, 112.0, "Dario Penwarden", "Same story: thick oil gives a high pressure drop across "
     "the filter. Wait for the oil to warm up, then check again."),
    (112.5, 121.0, "Greta Vollan", "Let me add the safety points. First, ice. When A7001 ice "
     "detection is active, the turbine stops by itself."),
    (121.5, 130.0, "Greta Vollan", "Keep at least 300 metres away from a turbine with ice on the "
     "blades, and no climbing until the ice has gone."),
    (130.5, 140.0, "Greta Vollan", "Second, people. Wear layers, take spare gloves and hand "
     "warmers, and do a buddy check every thirty minutes."),
    (140.5, 149.0, "Greta Vollan", "Ladder rungs can be frozen at the tower base. Use the service "
     "lift when it works, and check the lift battery on cold mornings."),
    (149.5, 157.0, "\u00c9lise Ternaux", "The service lift on WTG-06 stopped twice last winter "
     "because of the cold."),
    (157.5, 165.0, "Greta Vollan", "Good point. Report it every time, so that we can follow it "
     "up with Litware."),
    (165.5, 175.0, "Dario Penwarden", "Last thing: after the conversion, never top up a gearbox "
     "with PWG 320. The old drums are marked do not use."),
    (175.5, 183.0, "Callum Rydings", "There is still one drum of PWG 320 in the store."),
    (183.5, 191.0, "Dario Penwarden", "It stays there until the waste carrier takes it. Do not "
     "use it."),
    (191.5, 199.0, "Greta Vollan", "Please sign the attendance sheet before you leave. Thank "
     "you."),
    (199.5, 203.0, None, STAMP),
]


def _ts(seconds: float) -> str:
    hours, rest = divmod(round(seconds * 1000), 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def toolbox_talk(w: World) -> str:
    lines = [
        "WEBVTT",
        "",
        "NOTE",
        "Toolbox talk at the Quellmoor Ridge O&M building on 2025-11-12 at 07:30.",
        "Speakers: Dario Penwarden, Greta Vollan, Callum Rydings, \u00c9lise Ternaux.",
        "",
    ]
    for index, (start, end, speaker, text) in enumerate(_CUES, start=1):
        lines.append(str(index))
        lines.append(f"{_ts(start)} --> {_ts(end)}")
        lines.append(f"<v {speaker}>{text}" if speaker else text)
        lines.append("")
    return "\n".join(lines)
