"""Conservative accepted wording, never a keyword-count semantic grader."""
import re

def short_match(answer,expected,normalize):
    accepted={normalize(s) for s in expected if s}
    if normalize(answer) in accepted:
        return 'exact'
    value=answer.strip()
    # Strip only whole-answer presentation wrappers; arbitrary extra claims stay pending.
    value=re.sub(r'^(?:정답|답)(?:은|는|:|：)\s*','',value)
    value=re.sub(r'(?:이라고\s*(?:생각합니다|합니다)|라고\s*(?:생각합니다|합니다)|입니다|이다|이라고|라고|이요|이에요|예요)\s*[.!。]*$','',value)
    value=value.strip(' \t\r\n\"\'“”‘’')
    if normalize(value) in accepted:
        return 'wrapper'
    if any(len(term)>=2 and term in normalize(answer) for term in accepted):
        return 'review'
    return None
