import streamlit as st
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

st.set_page_config(page_title='WitOmni | Customer Return Simulator', page_icon='🛍️', layout='wide')
st.markdown('''<style>.block-container{max-width:1100px;padding-top:2rem}.hero{background:linear-gradient(120deg,#123e42,#216b67);color:white;padding:28px;border-radius:20px;margin-bottom:22px}.hero h1{color:white;margin:0;font-size:2.1rem}.hero p{color:#e4f6f1;margin:8px 0 0}.stButton button{background:#176e67;color:white;border-radius:10px;padding:.65rem 1.3rem;border:0}</style>''', unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>WitOmni · Customer Return Simulator</h1><p>Explore how customer shopping habits affect their chance of buying again.</p></div>',unsafe_allow_html=True)

FEATURES=['Recency','PurchaseFrequency','total_spent','AverageOrderValue','Tenure','AvgDaysBetweenOrders','UniqueProducts','OrdersLast90Days','IsUK']
@st.cache_resource(show_spinner='Training the prediction model on historical retail purchases (first launch may take a minute)…')
def train_model():
    url='https://archive.ics.uci.edu/static/public/352/data.csv'
    raw=pd.read_csv(url,encoding='latin1')
    raw=raw.drop_duplicates().dropna(subset=['CustomerID'])
    raw=raw[~raw['InvoiceNo'].astype(str).str.upper().str.startswith('C')]
    raw=raw[(raw.Quantity>0)&(raw.UnitPrice>0)]
    raw=raw[~raw.StockCode.astype(str).isin(['POST','DOT','C2','M','m','BANK CHARGES','AMAZONFEE','CRUK','S','D'])].copy()
    raw['InvoiceDate']=pd.to_datetime(raw.InvoiceDate)
    cutoff=raw.InvoiceDate.quantile(.7)
    past=raw[raw.InvoiceDate<=cutoff].copy()
    future=raw[raw.InvoiceDate>cutoff]
    past['TotalPrice']=past.Quantity*past.UnitPrice
    g=past.groupby('CustomerID')
    df=g.agg(total_spent=('TotalPrice','sum'),PurchaseFrequency=('InvoiceNo','nunique'),LastPurchaseDate=('InvoiceDate','max'),FirstPurchaseDate=('InvoiceDate','min'),UniqueProducts=('StockCode','nunique'),IsUK=('Country',lambda x:int(x.iloc[0]=='United Kingdom')))
    df['Recency']=(cutoff-df.LastPurchaseDate).dt.days
    df['AverageOrderValue']=df.total_spent/df.PurchaseFrequency
    df['Tenure']=(cutoff-df.FirstPurchaseDate).dt.days
    df['AvgDaysBetweenOrders']=np.where(df.PurchaseFrequency>1,(df.LastPurchaseDate-df.FirstPurchaseDate).dt.days/(df.PurchaseFrequency-1),df.Tenure)
    recent=past[past.InvoiceDate>cutoff-pd.Timedelta(days=90)]
    df['OrdersLast90Days']=recent.groupby('CustomerID').InvoiceNo.nunique().reindex(df.index,fill_value=0)
    df['target']=df.index.isin(set(future.CustomerID)).astype(int)
    X=df[FEATURES].fillna(0)
    y=df.target
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.2,random_state=42,stratify=y)
    model=XGBClassifier(n_estimators=100,max_depth=3,learning_rate=.01,random_state=42,eval_metric='logloss',n_jobs=2)
    model.fit(Xtr,ytr)
    auc=roc_auc_score(yte,model.predict_proba(Xte)[:,1])
    return model,auc,len(df),df[FEATURES].median(),cutoff

try:
    model,auc,n,medians,cutoff=train_model()
except Exception as e:
    st.error('Could not load the UCI Online Retail dataset. Please check internet access and try again.')
    st.code(str(e))
    st.stop()

m1,m2,m3=st.columns(3)
m1.metric('Historical customers',f'{n:,}')
m2.metric('Model test ROC-AUC',f'{auc:.3f}')
m3.metric('Prediction period','After Oct 7, 2011')
st.caption('Live-trained XGBoost with nine features from your notebook. The reported notebook best was 0.754; this app uses the documented baseline XGBoost settings, so its measured result may differ.')
st.subheader('Build a customer profile')
st.write('Change the values below to see what the model predicts. You do not need any statistics knowledge.')
with st.form('customer'):
    a,b=st.columns(2)
    with a:
        recency=st.slider('Days since last purchase',0,350,30,help='Smaller means they bought something more recently.')
        frequency=st.number_input('Total number of past orders',1,500,4)
        total=st.number_input('Total spent on products (£)',min_value=0.01,value=450.0,step=25.0)
        tenure=st.slider('Days since first purchase',0,380,180)
        unique=st.number_input('Different products purchased',1,2000,25)
    with b:
        avg=st.number_input('Average spend per order (£)',min_value=0.01,value=112.50,step=10.0)
        gap=st.slider('Average days between orders',0,380,45)
        recent=st.number_input('Orders in the last 90 days',0,500,2)
        country=st.selectbox('Customer location',['United Kingdom','Outside United Kingdom'])
        threshold=st.slider('Decision cutoff',.1,.9,.5,.05,help='A higher cutoff makes the model more cautious about predicting a return.')
    submit=st.form_submit_button('Predict customer behavior',use_container_width=True)
if submit:
    data=pd.DataFrame([[recency,frequency,total,avg,tenure,gap,unique,recent,int(country=='United Kingdom')]],columns=FEATURES)
    p=float(model.predict_proba(data)[0,1])
    returning=p>=threshold
    st.divider()
    st.subheader('Prediction for this customer')
    left,right=st.columns([1,1])
    with left:
        st.metric('Estimated chance of returning',f'{p:.1%}')
        st.progress(p)
        st.markdown('### '+('🟢 More likely to return' if returning else '🟠 Less likely to return'))
        st.write('The model estimates this customer is '+('more' if returning else 'less')+' likely to purchase again under the selected decision cutoff.')
    with right:
        st.markdown('**How to read this result**')
        st.write('Out of 100 customers with a similar model score, roughly '+str(round(p*100))+' would be expected to return **if the probabilities are well calibrated**. This is an estimate, not a guarantee.')
        st.write('**What you changed:** '+str(frequency)+' orders, last purchase '+str(recency)+' days ago, '+str(recent)+' orders in the last 90 days.')
        st.caption('Change one input at a time and predict again to explore how the score responds. These comparisons show model behavior, not causal effects.')
    st.info('Marketing interpretation: A low return score may identify a customer to consider for a re-engagement campaign. A high score may identify a likely repeat purchaser. The right action depends on campaign costs and goals.')
else:
    st.info('Set up a customer profile above and click **Predict customer behavior** to see the result.')
with st.expander('About the model and important limitations'):
    st.write('The historical dataset is UCI Online Retail (December 2010–December 2011). Features come from transactions up to the 70% date cutoff; the label is whether the customer bought again after that date. This app retrains an XGBoost model with the baseline parameters shown in your notebook, not the exact tuned best estimator from its later grid search. The historical 2011 return outcome is not a modern live churn forecast. Model probabilities are not calibrated, and manually entered combinations may be unlike real customer histories. The cutoff is adjustable for demonstration, not optimized for campaign profit.')
