import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)

import os
from argparse import ArgumentParser

import pandas as pd
from colorama import Fore, Style
from datasets import load_dataset, get_availabel_datasets
from mechanisms import privatize, available_mechanisms
from tasks import LearningTask, ErrorEstimation
from pytorch_lightning import seed_everything

seed_everything(12345)

private_node_ratios = [.2, .4, .6, .8, 1]
private_feature_ratios = [.2, .4, .6, .8, 1]
epsilons = [1, 3, 5, 7, 9]
epsilons_priv_ratio = [1, 3, 5]


def get_pnr_pfr_lists(feature, pnr_list, pfr_list):
    if feature == 'bit':
        return {(pnr, 1) for pnr in pnr_list} | {(1, pfr) for pfr in pfr_list}
    elif feature in available_mechanisms:
        return [(1, 1)]
    else:
        return [(0, 0)]


def get_eps_list(feature, pnr, pfr):
    if feature == 'bit':
        if pnr == 1 and pfr == 1:
            return epsilons
        else:
            return epsilons_priv_ratio
    elif feature in available_mechanisms:
        return epsilons
    else:
        return [1]


def save_results(task_name, dataset_name, feature, results, output):
    df_result = pd.DataFrame(
        data=results,
        columns=['method', 'pnr', 'pfr', 'eps', 'run', 'perf']
    )

    path = os.path.join(output, f'{task_name}_{dataset_name}_gcn_{feature}.pkl')
    df_result.to_pickle(path)


def error_estimation(args):
    for dataset_name in args.datasets:
        dataset = load_dataset(dataset_name).to('cuda')
        for feature in available_mechanisms & set(args.features):
            results = []
            for pnr, pfr in get_pnr_pfr_lists(feature, args.pnr_list, args.pfr_list):
                for eps in epsilons:
                    for run in range(args.repeats):
                        print(
                            Fore.BLUE +
                            f'\ntask=errorest / dataset={dataset_name} / model=gcn / '
                            f'feature={feature} / pnr={pnr} / pfr={pfr} / eps={eps} / run={run}'
                            + Style.RESET_ALL
                        )

                        data = privatize(dataset, pnr=pnr, pfr=pfr, eps=eps, method=feature)
                        t = ErrorEstimation(data=data, orig_features=dataset.x)
                        result = t.run()
                        results.append((f'gcn+{feature}', pnr, pfr, eps, run, result))

            save_results('errorest', dataset_name, feature, results, args.output)


def prediction(task, args):
    for dataset_name in args.datasets:
        dataset = load_dataset(dataset_name, split_edges=(task == 'linkpred'))
        dataset = dataset.to('cuda')

        for feature in args.features:
            results = []
            pr_list = get_pnr_pfr_lists(feature, args.pnr_list, args.pfr_list)

            for pnr, pfr in pr_list:
                for eps in get_eps_list(feature, pnr, pfr):
                    for run in range(args.repeats):
                        print(
                            Fore.BLUE +
                            f'\ntask={task} / dataset={dataset_name} / model=gcn / '
                            f'feature={feature} / pnr={pnr} / pfr={pfr} / eps={eps} / run={run}'
                            + Style.RESET_ALL
                        )

                        data = privatize(dataset, pnr=pnr, pfr=pfr, eps=eps, method=feature)
                        t = LearningTask(task_name=task, data=data)
                        result = t.run()
                        print(result)
                        results.append((f'gcn+{feature}', pnr, pfr, eps, run, result))

            save_results(task, dataset_name, feature, results, args.output)


def main(args):
    for task in args.tasks:
        if task in ['nodeclass', 'linkpred']:
            prediction(task, args)
        elif task == 'errorest':
            error_estimation(args)
        elif task == 'visualize':
            raise NotImplementedError


if __name__ == '__main__':
    task_choices = ['nodeclass', 'linkpred', 'errorest', 'visualize']
    dataset_choices = get_availabel_datasets()
    feature_choices = ['raw'] + list(available_mechanisms)
    parser = ArgumentParser()
    parser.add_argument('-t', '--tasks', nargs='*', choices=task_choices, default=task_choices)
    parser.add_argument('-d', '--datasets', nargs='*', choices=dataset_choices, default=dataset_choices)
    parser.add_argument('-f', '--features', nargs='*', choices=feature_choices, default=feature_choices)
    parser.add_argument('-r', '--repeats', type=int, default=10)
    parser.add_argument('-o', '--output', type=str, default='results')
    parser.add_argument('--pnr', nargs='*', type=float, default=private_node_ratios, dest='pnr_list')
    parser.add_argument('--pfr', nargs='*', type=float, default=private_feature_ratios, dest='pfr_list')
    parser.add_argument('--eps', nargs='*', type=float, default=epsilons, dest='epsilons')

    arguments = parser.parse_args()
    print(arguments)
    epsilons = arguments.epsilons

    main(arguments)
