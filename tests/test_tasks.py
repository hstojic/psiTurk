import pytest

@pytest.fixture()
def campaign():
    from psiturk.models import Campaign
    parameters = {
        'codeversion': '1.0',
        'mode': 'sandbox',
        'goal': 100,
        'minutes_between_rounds': 1,
        'assignments_per_round': 10,
        'hit_reward': 1.00,
        'hit_duration_hours': 1,
    }
    new_campaign = Campaign(**parameters)
    
    from psiturk.db import db_session
    db_session.add(new_campaign)
    db_session.commit()
    return new_campaign

def test_campaign_round_codeversion_change_cancel(patch_aws_services, campaign, mocker, caplog):
    from psiturk.tasks import do_campaign_round
    
    campaign_args = {
        'campaign': campaign,
        'job_id': campaign.campaign_job_id
    }
    
    from psiturk.experiment import app
    mocker.patch.object(app.apscheduler,
        'remove_job', lambda *args, **kwargs: True)
    
    from psiturk.amt_services_wrapper import MTurkServicesWrapper
    aws_services_wrapper = MTurkServicesWrapper()
    aws_services_wrapper.config['Task Parameters']['experiment_code_version'] = '1.1'
    
    import psiturk.tasks
    mocker.patch.object(psiturk.tasks.TaskUtils, 'aws_services_wrapper', aws_services_wrapper)
    
    
    import psiturk.experiment    
    remove_job_mock = mocker.patch.object(psiturk.experiment.app.apscheduler, 'remove_job')
    do_campaign_round(**campaign_args)
    remove_job_mock.assert_called()
    
def test_campaign_goal_met_cancel(patch_aws_services, campaign, mocker, caplog, stubber):
    from psiturk.tasks import do_campaign_round
    
    campaign_args = {
        'campaign': campaign,
        'job_id': campaign.campaign_job_id
    }
    
    from psiturk.experiment import app
    mocker.patch.object(app.apscheduler,
        'remove_job', lambda *args, **kwargs: True)
        
    import psiturk.tasks
    mocker.patch.object(psiturk.models.Participant, 'count_completed', lambda *args, **kwargs: campaign.goal)
    
    import psiturk.experiment
    remove_job_mock = mocker.patch.object(psiturk.experiment.app.apscheduler, 'remove_job')
    do_campaign_round(**campaign_args)
    remove_job_mock.assert_called()
    
def test_campaign_posts_hits(patch_aws_services, stubber, campaign, mocker, caplog):
    
    from psiturk.amt_services_wrapper import MTurkServicesWrapper
    aws_services_wrapper = MTurkServicesWrapper()
    
    
    import psiturk.tasks
    mocker.patch.object(psiturk.tasks.TaskUtils, 'aws_services_wrapper', aws_services_wrapper)
    mocked_create_hit = mocker.patch.object(aws_services_wrapper, 'create_hit')
    
    campaign_args = {
        'campaign': campaign,
        'job_id': campaign.campaign_job_id
    }
    from psiturk.tasks import do_campaign_round
    do_campaign_round(**campaign_args)
    
    assert mocked_create_hit.call_count == 2
    mocked_create_hit.assert_any_call(num_workers=9, reward=campaign.hit_reward, duration=campaign.hit_duration_hours)
    mocked_create_hit.assert_any_call(num_workers=1, reward=campaign.hit_reward, duration=campaign.hit_duration_hours)
    