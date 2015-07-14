"""Tools to work with Beaker (https://beaker-project.org/).

Note that you need `bkr` command available (comes from beaker-client package)
and configured. See:

https://beaker-project.org/docs/user-guide/bkr-client.html#installing-and-configuring-the-client
"""

import subprocess
import xml.dom.minidom


def _beaker_process_recipe(recipe):
    """Process recipe and return info about it

    :param str recipe: recipe (or guestrecipe) element to process

    """
    recipe_info = {}
    res_task = False
    res_tag = False
    recipe_info['id'] = int(recipe.attributes['id'].value)
    recipe_info['system'] = recipe.attributes['system'].value
    recipe_info['arch'] = recipe.attributes['arch'].value
    recipe_info['distro'] = recipe.attributes['distro'].value
    recipe_info['variant'] = recipe.attributes['variant'].value
    # Do we have /distribution/reservesys? If so, status is based on that.
    tasks = recipe.getElementsByTagName("task")
    for task in reversed(tasks):
        if task.attributes['name'].value == '/distribution/reservesys':
            res_task = task
            break
    # Do we have <reservesys>? If so, status is recipe.status.
    reservesyss = recipe.getElementsByTagName("reservesys")
    for reservesys in reservesyss:
        res_tag = True
        break
    # Determine status of the recipe/system reservation
    if res_tag and not res_task:
        recipe_info['reservation'] = recipe.attributes['status'].value
    elif res_task and not res_tag:
        recipe_info['reservation'] = res_task.attributes['status'].value
    elif res_task and res_tag:
        recipe_info['reservation'] = "ERROR: Looks like the recipe " + \
                                     "for this system have too many " + \
                                     "methods to reserve. Do not know " + \
                                     "what happens."
    else:
        recipe_info['reservation'] = recipe.attributes['status'].value
    return recipe_info


def beaker_jobid_to_system_info(jobID):
    """Get system reservation task status (plus other info) based on
    Beaker jobID.

    This function requires configured bkr utility. We parse everithing from
    `bkr job-results [--prettyxml] J:123456`, so if you see some breakage,
    please capture that output.

    For testing putposes, if you provide file descriptor instead of jobID,
    XML will be loaded from there.

    :param str jobID: ID of a Beaker job (e.g. 'J:123456')

    """
    systems = []

    # Get TML with job results and create DOM object
    if hasattr(jobID, 'read'):
        dom = xml.dom.minidom.parse(jobID)
    else:
        out = subprocess.check_output(['bkr', 'job-results', jobID])
        dom = xml.dom.minidom.parseString(out)

    # Parse the DOM object. The XML have structure like this (all elements
    # except '<job>' can appear more times):
    #   <job id='123' ...
    #     <recipeSet id='456' ...
    #       <recipe id='789' system='some.system.example.com'
    #         status='Reserved' ...
    #       <recipe id='790' system='another.system.example.com'
    #         status='Completed' ...
    #         <guestrecipe id='147258' ...
    #     </recipeSet>
    #     <recipeSet id='457' ...
    #       ...
    jobs = dom.getElementsByTagName("job")
    for job in jobs:
        recipeSets = job.getElementsByTagName("recipeSet")
        for recipeSet in recipeSets:
            recipes = recipeSet.getElementsByTagName("recipe")
            for recipe in recipes:
                systems.append(_beaker_process_recipe(recipe))
                guestrecipes = recipe.getElementsByTagName("guestrecipe")
                for guestrecipe in guestrecipes:
                    systems.append(_beaker_process_recipe(guestrecipe))
    return systems

if __name__ == "__main__":
    import pprint
    pprint.pprint(beaker_jobid_to_system_info(open('a.xml')))
