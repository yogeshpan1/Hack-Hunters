"""Explicit, one-time demonstration overlay; never runs during normal startup."""
from copy import deepcopy

from . import models as m
from .scheduling import conflicts, enriched, patterns_overlap, snapshot, solve
from .services import audit, bump, revision

ACTION = 'OPTIMIZATION DEMO CONFLICTS ADDED'


def add_demo_conflicts(db):
    if db.first(m.AuditLog, {'action': ACTION}):
        return {'status': 'Already applied; existing timetable preserved'}
    admin = db.first(m.User, {'role': 'SuperAdmin', 'active': True})
    if not admin:
        raise ValueError('An active SuperAdmin is required for the demo audit.')
    expected = revision(db)
    data = snapshot(db)
    planned = deepcopy(data)
    baseline = {issue['id'] for issue in conflicts(data)}
    used = set()
    moves = []
    for session in enriched(data):
        if session['locked'] or session['id'] in used:
            continue
        for target in enriched(data):
            if target['id'] == session['id'] or target['id'] in used:
                continue
            if session['room_id'] == target['room_id'] or session['day'] != target['day']:
                continue
            if not patterns_overlap(session['week_pattern'], target['week_pattern']):
                continue
            if session['start'] >= target['start'] + target['duration'] or target['start'] >= session['start'] + session['duration']:
                continue
            row = next(row for row in planned['sessions'] if row['id'] == session['id'])
            original_room = row['room_id']
            row['room_id'] = target['room_id']
            added = [issue for issue in conflicts(planned) if issue['id'] not in baseline]
            # Add exactly one room double-booking per move, without introducing
            # capacity, equipment, availability, or academic-policy violations.
            if len(added) == len(moves) + 1 and all(issue['kind'] == 'Room clash' for issue in added):
                moves.append({'session_id': session['id'], 'previous_room_id': original_room,
                              'room_id': target['room_id'], 'overlaps_session_id': target['id']})
                used.update([session['id'], target['id']])
                break
            row['room_id'] = original_room
        if len(moves) == 2:
            break
    if len(moves) != 2:
        raise ValueError('Could not find two suitable demo clashes; no changes saved.')
    result = solve(planned)
    if result['status'] != 'Review' or conflicts(planned, result['assignments']):
        raise ValueError('Optimizer could not validate a conflict-free solution; no changes saved.')
    for move in moves:
        session = db.get(m.TimetableSession, move['session_id'])
        session.room_id = move['room_id']
        session.notes += (f" DEMO CONFLICT: room double-booked with session {move['overlaps_session_id']} "
                          f"for Optimization Lab practice; previous room ID {move['previous_room_id']}. "
                          'This is a demonstration change, not a source-routine error.')
    bump(db, expected)
    audit(db, admin, ACTION, 'Timetable', previous={'conflicts': len(baseline)},
          new={'moves': moves, 'conflicts': len(conflicts(planned))},
          reason='User requested resolvable timetable conflicts for optimization practice.',
          result='Two room clashes added; zero-conflict solution verified but not published')
    db.commit()
    return {'status': 'Applied', 'moves': moves, 'conflicts': len(conflicts(planned)),
            'verified_solution_conflicts': 0}
