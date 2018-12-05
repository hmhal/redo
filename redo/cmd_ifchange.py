import os, sys, traceback
import env, state, builder, jobserver, deps
from logs import debug2, err


def should_build(t):
    f = state.File(name=t)
    if f.is_failed():
        raise builder.ImmediateReturn(32)
    dirty = deps.isdirty(f, depth='', max_changed=env.v.RUNID,
                         already_checked=[])
    return f.is_generated, dirty == [f] and deps.DIRTY or dirty


def main():
    rv = 202
    try:
        targets = sys.argv[1:]
        state.init(targets)
        if env.is_toplevel and not targets:
            targets = ['all']
        if env.is_toplevel and env.v.LOG:
            builder.close_stdin()
            builder.start_stdin_log_reader(
                status=True, details=True,
                pretty=True, color=True, debug_locks=False, debug_pids=False)
        if env.v.TARGET and not env.v.UNLOCKED:
            me = os.path.join(env.v.STARTDIR,
                              os.path.join(env.v.PWD, env.v.TARGET))
            f = state.File(name=me)
            debug2('TARGET: %r %r %r\n'
                   % (env.v.STARTDIR, env.v.PWD, env.v.TARGET))
        else:
            f = me = None
            debug2('redo-ifchange: not adding depends.\n')
        jobserver.setup(1)
        try:
            if f:
                for t in targets:
                    f.add_dep('m', t)
                f.save()
                state.commit()
            rv = builder.main(targets, should_build)
        finally:
            try:
                state.rollback()
            finally:
                try:
                    jobserver.force_return_tokens()
                except Exception, e:  # pylint: disable=broad-except
                    traceback.print_exc(100, sys.stderr)
                    err('unexpected error: %r\n' % e)
                    rv = 1
    except KeyboardInterrupt:
        if env.is_toplevel:
            builder.await_log_reader()
        sys.exit(200)
    state.commit()
    if env.is_toplevel:
        builder.await_log_reader()
    sys.exit(rv)


if __name__ == '__main__':
    main()