import datetime as dt
import itertools

from django import forms
#from crispy_forms.helper import FormHelper
#from crispy_forms_foundation.layout  import Layout, Row, Column, Fieldset, Field, SplitDateTimeField, RowFluid, Column, Div, ButtonHolder, Submit, HTML

#from django.forms.extras.widgets import RadioSelect

from resv import models as m

class RanchSearchForm(forms.Form):
    RANCHES = [(ranch.id, ranch.display_name()) for ranch in m.Ranch.objects.all()]
#    RANCHES = [(1, 'test')]
    ranch = forms.MultipleChoiceField(choices=RANCHES, required=False, widget=forms.SelectMultiple(attrs={'style':'width:100%'}))#, initial='Enter ranch name or number'

    GAME = [('', '')] + [(game.id, game.name) for game in m.Game.objects.all()]
    game = forms.ChoiceField(choices=GAME, required=False, widget=forms.Select(attrs={'style':'width:100%;height:100%'}))
    

    start_date = forms.DateField(initial=dt.date.today, widget=forms.DateInput(format = '%m/%d/%Y'), input_formats=('%m/%d/%Y',), required=False)

    CLUSTERS = [('', '')] + [(cluster.id, cluster.name) for cluster in m.Cluster.objects.all()]
    cluster = forms.ChoiceField(choices=CLUSTERS, required=False,  widget=forms.Select(attrs={'style':'width:100%'}))  

    DFGZONES = [('', '')] + [(zone.id, zone.name) for zone in m.GameRegion.objects.all()]
    DFGZone = forms.ChoiceField(choices=DFGZONES, required=False,  widget=forms.Select(attrs={'style':'width:100%'}))  

    allows_dogs = forms.ChoiceField(required=False, choices=(('0,1',""),('1','Yes'),('0', 'No')), widget=forms.Select(attrs={'style':'width:100%'}))
    archery = forms.ChoiceField(required=False, choices=(('0', 'General'),('1','Archery only'),('0,1', 'All ranches')), widget=forms.Select(attrs={'style':'width:100%'}))
    
    resv = forms.CharField(max_length=20, required=True)
    r = '''
    def __init__(self, *args,  **kwargs):
        self.helper = FormHelper()
        #self.helper.form_action = '/search/'
        #self.helper.form_method = 'GET'

        self.helper.form_id = 'ranchsearch'
        self.helper.layout = Layout(            
            Row(
                Column(Field('ranch', style='width:100%'), css_class='large-4 columns'),
                Column(Field('game', style='width:100%;height:100%;'), css_class='large-4 columns'),
                Column(Field('start_date', style='width:100%'), css_class='large-4 columns'),
            ),
            
            Row(
                Column(Field('cluster', style='width:100%'), css_class='large-6 columns'),
                Column(Field('DFGZone', style='width:100%'), css_class='large-6 columns'),
            ),
            HTML("<p></p>"),
            Row(
                Column(Field('allows_dogs', style='width:100%'), css_class='large-4 columns'),
                Column(Field('archery', style='width:100%'), css_class='large-6 columns'),
            ),
            HTML("<p></p>"),
            Row(Submit('Search', 'Search')),
            Field('resv', type='hidden')
        )
        super(RanchSearchForm, self).__init__(*args, **kwargs)
'''

def make_person_form_field(index, kind, valid):
   # print 'making person form field'
    if valid:
   #     print 'is valid', '{0}_{1}'.format(kind, index)
        return Column(Field('{0}_{1}'.format(kind, index), style='width:100%'), css_class='large-6 columns') 
    else:
   #     print 'is blank'
        return Column(css_class='large-6 columns') 
def make_person_form_row(index, hunter=True, nonhunter=True):
  #  print 'making person form row'
    return Row(
        Column(
            make_person_form_field(index, 'hunter', hunter),
            make_person_form_field(index, 'nonhunter', nonhunter),
            css_class='large-8 large-centered columns'
            ),
            id='person_{0}'.format(index)
        )

#class SegDatesGameForm(forms.Form):
#    seg = forms.CharField(max_length=20, required=True)
#    self.fields['game'] = forms.ChoiceField(choices=[(game.id, game.name) for game in ranch.get_game()], required=True, label='Game:')
#    def __init__(self, *args, **kwargs):

class StandbyChoice(forms.Form):
    resv = forms.CharField(max_length=20, required=True)
    seg = forms.CharField(max_length=20, required=True)
    owner = forms.IntegerField(required=True)
    
    def __init__(self, *args, **kwargs):
        seg_obj = m.ResvSegment.objects.get(id=self.seg)
        self.helper = FormHelper()
        self.helper.form_id = 'standbychoice'
        self.helper.form_action = '/standbychoice/save/'
        self.helper.form_method = 'POST'
        layout_elements = [ Field('resv', type='hidden'),
            Field('seg', type='hidden'),
            Field('owner', type='hidden')
            ]
        for person in seg_obj.get_persons():
            col = []
            for di in (seg_obj.start_date + dt.timedelta(days=n) for n in range((seg_obj.end_date - seg_obj.start_date).days + 1)): 
                col.append(Column(Field('select_{0}_{1}'.format(person.id, di), style='width:100%'), css_class='large-1 columns'))
            layout_elements += Row(Column(*col, css_class='large-8 large-centered columns'))
                    
                
        self.helper.layout = Layout(*layout_elements)
        super(ResvSegForm, self).__init__(*args, **kwargs)
        self.fields['resv_ranch'] = forms.ChoiceField(choices=((ranch.id, ranch.display_name()),), required=True, label='Ranch:')

class ResvSegForm(forms.Form):
    resv = forms.CharField(max_length=20, required=True)
    seg = forms.CharField(max_length=20, required=True)
    owner = forms.IntegerField(required=True)
    


    def __init__(self,  *args, **kwargs):#, game_id, hunters, nonhunters, start_date, number_of_days, bring_dog, dog_comment):
        print 'create form called'
        print 'args', args
        print 'kwargs', kwargs
        if kwargs.has_key('initial'):
            print 'via kwargs'
           # print kwargs['initial'].get('owner', False)
            #owner_id = kwargs['initial'].__getitem__('owner')
            print kwargs['initial'].get('owner')
            print kwargs['initial'].get('owner')#[0]
            owner_id = kwargs['initial'].get('owner')#[0]
            blind_id = kwargs['initial'].get('resv_blind', False)
        else:
            owner_id = list(args[0].get('owner'))[0]
            blind_id = args[0].get('resv_blind', False)
        if type(blind_id) == type(['00']):
            blind_id = blind_id[0]
        print 'owner_id', owner_id
        print 'blind_id', blind_id
        
        
        person_layout = [make_person_form_row(index, hunter=True, nonhunter=True) for index in range(20)]
       # if kwargs.has_key('persons'):
        #    person_layout = [make_person_form_row(index, hunter=row[0], nonhunter=row[1]) for index, row in enumerate(itertools.izip_longest(kwargs['persons']['hunters'], kwargs['persons']['nonhunters']))]
       #     persons_arg = kwargs.pop('persons')
       # else:
         #   person_layout = [make_person_form_row(0, hunter=True, nonhunter=True),]
         #   print person_layout
       #     persons_arg = {}
       # init_show_rows = 2
       # if kwargs.has_key('initial'):
       #     kwargs['initial'].keys


        self.helper = FormHelper()
        self.helper.form_id = 'quickresv'
        self.helper.form_action = '/segment/save/'
        self.helper.form_method = 'POST'
        layout_elements = [ Field('resv', type='hidden'),
            Field('seg', type='hidden'),
            Field('owner', type='hidden'),
            Row(
                Column(
                    Column(Field('resv_ranch', style='width:100%'), css_class='large-6 columns'),
                    Column(Field('resv_blind', style='width:100%'), css_class='large-3 columns'),
                    Column(Field('resv_game', style='width:100%'), css_class='large-3 columns'),
                    css_class='large-8 large-centered columns'
                    )
                )
        ]
        layout_elements += person_layout
        layout_elements += [ 
            Row(Column(HTML('<div class="button small  small-5" id="add_person_row" onclick="add_person_row(1);">Add more people</div>'), 
                    css_class='large-6 large-offset-5')
                ),
            Row(
                Column(
                    Column(Field('resv_start_date', style='width:100%'), css_class='large-4 columns'),
                    Column(Field('resv_length', style='width:100%'), css_class='large-4 columns'),
                    css_class='large-8 large-centered columns'
                )
            ),
            Row(
                Column(
                    Column(Field('dog', style='width:100%'), css_class='large-4 columns'),
                    Column(Field('dog_comment', style='width:100%'), css_class='large-8 columns'),
                    css_class='large-8 large-centered columns'
                )
            ),
            Row(
                Column(Submit('savecontinue', 'Save and continue', css_class='button small'), css_class='large-5 small-12  columns') ,
                Column(Submit('savereview', 'Save and review reservation', css_class='button small'), css_class='large-5 small-12 columns'),
                HTML("<input type='submit' class='close-reveal-modal secondary button small ' value='Cancel'/>"),
                #Column(Submit('cancel', 'Cancel', css_class='secondary button small'), css_class='large-2 small-12 columns'),
                css_class='large-8 large-centered columns'
            ),
            Field('show_rows', type='hidden')
        ]
        self.helper.layout = Layout(*layout_elements)
        super(ResvSegForm, self).__init__(*args, **kwargs)
        print 'Im here0'
        print 'blind_id', blind_id
        blind = m.Blind.objects.get(pk=blind_id)
        ranch = blind.ranch
        print 'blind choices:', blind
        print blind.id
        self.fields['resv_ranch'] = forms.ChoiceField(choices=((ranch.id, ranch.display_name()),), required=True, label='Ranch:')
        
        self.fields['resv_blind'] = forms.ChoiceField(choices=((blind.id, blind.name),), required=True, label='Blind:')
        self.fields['resv_game'] = forms.ChoiceField(choices=[(game.id, game.name) for game in ranch.get_game()], required=True, label='Game:')
        # add seg
        hunter_list = [('', '---------')]
        hunter_list += [(h.id, h.get_long_name()) for h in m.Person.objects.get(pk=owner_id).family.person_set.all()]
        print 'Im here1'
    #    try:
    #        if persons_arg:
    #            print 'has persons_arg', persons_arg
    #            for row_num, row in enumerate(itertools.izip_longest(persons_arg['hunters'], persons_arg['nonhunters'])):
        
        print 'Im here2'
        init_show_rows = 2
        for row_num in range(20):
            for i in range(2):
                field_name = '{0}_{1}'.format(['hunter', 'nonhunter'][i], row_num)
                self.fields[field_name] = forms.ChoiceField(choices=hunter_list, required=False, label='{0} {1}'.format(['Hunter', 'Nonhunter'][i], row_num+1))    
                if kwargs.has_key('initial') and kwargs['initial'].has_key(field_name):
                    print 'has field', field_name
                    init_show_rows = max(init_show_rows, row_num+2)
        print 'here now'
        
        self.fields['resv_start_date'] = forms.DateField(required=True, widget=forms.DateInput(format = '%m/%d/%Y'), input_formats=('%m/%d/%Y',), label='Start date:')
        self.fields['resv_length'] = forms.IntegerField(initial=1, required=True, label='Number of days:')
        self.fields['dog'] = forms.ChoiceField(choices=((0,'No'), (1, 'Yes'),), label='Are you bringing a dog:')
        self.fields['dog_comment'] = forms.CharField(max_length=100, label='Notes about the dog for other guests:', required=False)        
        
        self.fields['show_rows'] = forms.IntegerField(required=False, initial=init_show_rows)

    def clean(self):
        cleaned_data = super(ResvSegForm, self).clean()
        for key, value in cleaned_data.items():
            if not value and key in self.initial:
                cleaned_data[key] = self.initial[key]
        return cleaned_data
   
    def save_for_later(self, user, blind_id, game_id, hunters, nonhunters, start_date, number_of_days, bring_dog, dog_comment):
        GAME = [(game.id, game.name) for game in m.Game.objects.all()] # change to ranch specific. 
        self.fields['game'] = forms.ChoiceField(choices=GAME, required=True, label='Game:')

        



        self.helper.layout = Layout(
            Row(
                Column(
                    Column(Field('resv_ranch', style='width:100%'), css_class='large-6 columns'),
                    Column(Field('resv_blind', style='width:100%'), css_class='large-3 columns'),
                    Column(Field('resv_game', style='width:100%'), css_class='large-3 columns'),
                    css_class='large-8 large-centered columns'
                    )
                ),
            Row(
                Column(
                    Column(Field('hunter_1', style='width:100%'), css_class='large-6 columns'),
                    Column(Field('nonhunter_1', style='width:100%'), css_class='large-6 columns'),
                    css_class='large-8 large-centered columns'
                )
            ),
            Row(
                Column(
                    Column(Field('resv_start_state', style='width:100%'), css_class='large-4 columns'),
                    Column(Field('resv_length', style='width:100%'), css_class='large-4 columns'),
                    css_class='large-8 large-centered columns'
                )
            ),
            Row(
                Column(
                    Column(Field('dog', style='width:100%'), css_class='large-4 columns'),
                    Column(Field('dog_comment', style='width:100%'), css_class='large-8 columns'),
                    css_class='large-8 large-centered columns'
                )
            ),
        )





