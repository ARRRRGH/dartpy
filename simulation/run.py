import os
import shutil
import subprocess as sp
from joblib import Parallel, delayed
from shutil import copytree, copyfile, rmtree, move

import utils.general


class Runner(object):
    """
    Runner class schedules run executions.
    """

    def __init__(self, runs, n_jobs=1, *args, **kwargs):

        self.runs = runs
        self.jobs = []
        self.n_jobs = n_jobs

        # TODO: check if simulation paths are up to date
        # TODO: merge runs with run params in simulation.params then save simulation

    def _create_jobs(self, *args, **kwargs):
        if type(self.runs) is list:
            for runner in self.runs:
                if type(runner) is list:
                    self.jobs.append(delayed(RunEnvironment(runs=self.runs, *args, **kwargs)).run)
                elif type(runner) is str:
                    self.jobs.append(delayed(SimulationRunner(runner).run)(*args, **kwargs))
                elif type(runner) is SimulationRunner:
                    self.jobs.append(delayed(runner.run)(*args, **kwargs))
                elif type(runner) is dict:
                    if 'runs' in runner:
                        self.jobs.append(delayed(RunEnvironment(runs=runner['sequence'], **runner).run))
                else:
                    self.jobs.append(delayed(runner.run))
        else:
            raise Exception('runs must be a list of simulations or paths to simulations or else valid' + ' runs dicts.')

    def run(self, *args, **kwargs):
        self._create_jobs(*args, **kwargs)
        Parallel(n_jobs=self.n_jobs)(self.jobs)


class RunEnvironment(Runner):
    """
    A run environment can load the needed databases and run simulations with these databases either sequentially or
    in parallel. It copies simulations to the dart directory if necessary.
    """

    def __init__(self, keep_maket=False, keep_dtm=False, update_atmosphere_hook=None, update_lambertian_hook=None,
                 update_vegetation_hook=None, *args, **kwargs):
        Runner.__init__(*args, **kwargs)

        self.update_atmosphere_hook = update_atmosphere_hook
        self.update_lambertian_hook = update_lambertian_hook
        self.update_vegetation_hook = update_vegetation_hook

        self.keep_maket = keep_maket
        self.keep_dtm = keep_dtm

        self.db_update = db_update

        runner0 = self.runs[0]
        if runner0 is str:
            runner0 = SimulationRunner(runner0)

        self.dart_path = runner0.simulation.dart_path
        if not os.path.exists(self.dart_path):
            raise Exception('No valid dart_path is set.')

        self.version = runner0.simulation.version

        # prepare first run
        self._create_db(runner0.simulation)
        self.prepare(runner0.simulation)

        if len(self.runs) > 1:
            # calls that need to be processed sequentially
            other_simulations = [run.simulation for run in self.runs[1:]]
            map(self.prepare, other_simulations)

            runner0.prepare()

            if self.keep_maket:
                self._copy_maket(runner0.simulation, other_simulations)
            if self.keep_dtm:
                self._copy_dtm(runner0.simulation, other_simulations)

            # append completing to jobs in order to include it in the parallelisation
            self.jobs.append(delayed(runner0.complete)(*args, **kwargs))
        else:
            self.jobs.append(delayed(runner0.run)(*args, **kwargs))

    def _create_jobs(self, *args, **kwargs):
        if len(self.runs) > 1:
            for i, runner in enumerate(self.runs[1:]):
                if not type(runner) is str or type(runner) is SimulationRunner:
                    raise Exception('runs must be list of str or SimulationRunners')

                if type(runner) is str:
                    runner = SimulationRunner(runner, *args, **kwargs)

                id_runner = _get_simulation_name(runner.simulation)
                if runner.version != self.version:
                    raise Exception(id_runner + ' has not same version as other simulations in RunEnvironment.')

                if runner.dart_path != self.dart_path:
                    raise Exception(id_runner + ' has not same dart_path as other simulations in RunEnvironment.')

                self.jobs.append(delayed(runner.run)(*args, **kwargs))

        self.jobs.append(delayed(self._restore_db))

    def prepare(self, simulation):
        sim_loc = utils.general.create_path(self.dart_path, 'user_data' 'simulations')

        _simulation_name = _get_simulation_name(simulation)
        _working_dir = os.path.abspath(utils.general.create_path(sim_loc, _simulation_name))

        # TODO: does folder *really* need to be in DART directory?
        does_sim_name_exist = os.path.exists(_working_dir)
        if not simulation.path.startswith(os.path.abspath(self.dart_path)):
            if not does_sim_name_exist:
                shutil.copytree(simulation.path, _working_dir)  # Update simulation params
            else:
                raise Exception(
                    'Simulation with the name ' + _simulation_name + ' does already exist in simulation directory.')
        else:
            pass

    def _create_db(self, simulation):
        if self.update_atmosphere_hook is not None or self.update_lambertian_hook is not None \
                or self.update_vegetation_hook is not None:

            # copy existing db to safe place
            db_path = utils.general.create_path(simulation.dart_path, 'database')
            copytree(db_path, utils.general.create_path(simulation.dart_path, 'orig_database'))

            # apply hooks
            if self.update_atmosphere_hook is not None:
                self.update_atmosphere_hook(simulation, db_path)

            if self.update_vegetation_hook is not None:
                self.update_atmosphere_hook(simulation, db_path)

            if self.update_lambertian_hook is not None:
                self.update_atmosphere_hook(simulation, db_path)

    def _copy_maket(self, src_simulation, other_simulations):
        create_maket_path = lambda simu: utils.general.create_path(self.dart_path, 'user_data', 'simulations',
                                                                   _get_simulation_name(simu), 'output', 'maket.txt')

        src_path = create_maket_path(src_simulation)
        other_paths = [create_maket_path(other) for other in other_simulations]
        for other in other_paths:
            copyfile(src_path, other)

    def _copy_dtm(self, src_simulation, other_simulations):
        create_dtm_path = lambda simu: utils.general.create_path(self.dart_path, 'user_data', 'simulations',
                                                                 _get_simulation_name(simu), 'output', 'dtm.bin')

        src_path = create_dtm_path(src_simulation)
        other_paths = [create_dtm_path(other) for other in other_simulations]
        for other in other_paths:
            copyfile(src_path, other)

    def _restore_db(self):
        rmtree(utils.general.create_path(self.dart_path, 'database'))
        move(utils.general.create_path(self.dart_path, 'orig_database'),
             utils.general.create_path(self.dart_path, 'database'))


def _get_simulation_name(simulation):
    fold, _simulation_name = os.path.split(simulation.path)
    return _simulation_name


class SimulationRunner(object):
    """
    Class dispatching and handling the run of a single simulation.
    """

    def __init__(self, simulation, post_maket_hook=None, create_dtm_hook=None, *args, **kwargs):

        self.simulation = simulation

        self.create_dtm_hook = create_dtm_hook
        self.post_maket_hook = post_maket_hook

        self.working_dir = None
        self.simulation_name = _get_simulation_name(self.simulation)
        self.dart_path = simulation.dart_path

    def run(self, only_prepare=False, *args, **kwargs):
        self.prepare(*args, *kwargs)
        if not only_prepare:
            self.complete(*args, **kwargs)

    def prepare(self, *args, **kwargs):
        self._dart_prep_runs(*args, **kwargs)

    def complete(self, *args, **kwargs):
        self._run_dart_only(*args, **kwargs)

    def _dart_prep_runs(self, *args, **kwargs):
        # TODO: find out if order matters, if not run this multithreaded
        self._run_dem(*args, **kwargs)
        self._run_direction(*args, **kwargs)
        self._run_phase(*args, **kwargs)
        self._run_maket(*args, **kwargs)
        self._run_atmosphere(*args, **kwargs)

    def _dart_run(self, *args, **kwargs):
        self._dart_prep_runs(*args, **kwargs)
        self._run_dart_only(*args, **kwargs)

    def _run_dem(self, shell=True):
        if self.create_dtm_hook is not None:
            self.create_dtm_hook(self.simulation)
        cmd = utils.general.create_path(self.dart_path, 'tools/linux/dart-dem-edit.sh') + ' ' + self.simulation_name
        p = sp.Popen(cmd, shell=shell)
        return p.communicate()

    def _run_direction(self, shell=True):
        cmd = utils.general.create_path(self.dart_path, 'tools/linux/dart-directions.sh') + ' ' + self.simulation_name
        p = sp.Popen(cmd, shell=shell)
        return p.communicate()

    def _run_maket(self, shell=True):
        cmd = utils.general.create_path(self.dart_path, 'tools/linux/dart-maket-edit.sh') + ' ' + self.simulation_name
        p = sp.Popen(cmd, shell=shell)
        if self.post_maket_hook is not None:
            out_path = utils.general.create_path(self.dart_path, 'output')
            self.post_maket_hook(self.simulation, out_path)
        return p.communicate()

    def _run_phase(self, shell=True):
        cmd = utils.general.create_path(self.dart_path, 'tools/linux/dart-phase-edit.sh') + ' ' + self.simulation_name
        p = sp.Popen(cmd, shell=shell)
        return p.communicate()

    def _run_atmosphere(self, shell=True):
        cmd = utils.general.create_path(self.dart_path, 'tools/linux/dart-atmosphere-edit.sh') + ' ' \
              + self.simulation_name
        p = sp.Popen(cmd, shell=shell)
        return p.communicate()

    def _run_dart_only(self, shell=True):
        cmd = utils.general.create_path(self.dart_path, 'tools/linux/dart-only.sh') + ' ' + self.simulation_name
        p = sp.Popen(cmd, shell=shell)
        return p.communicate()


def run(obj, *args, **kwargs):
    Runner(run, *args, **kwargs).run(*args, **kwargs)


