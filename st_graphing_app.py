import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import base64

# Load in data
st.title("CSV File Uploader and Data Processing")

uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    st.write("Uploaded file:")
    st.write(uploaded_file.name)

    data = pd.read_csv(uploaded_file, delimiter=',')

    data = data[['Sample name','Subsample name','Initial pH','System Name', 'Test time','wt% carb', 'BiCarb', \
                 'Adj Carb', 'Adj BiCarb', 'Determination start']]
    columns_to_convert = ['wt% carb', 'BiCarb', 'Adj Carb', 'Adj BiCarb', 'Initial pH', 'Test time']
    data[columns_to_convert] = data[columns_to_convert].astype('float')
    data['Determination start'] = data['Determination start'].str.strip('Z')
    data['time elapsed'] = (pd.to_datetime(data['Determination start']) - pd.to_datetime(data['Determination start'].iloc[0])).dt.total_seconds()/60

    st.write('Processed CSV file content:')
    st.write(data)

    std_carb = st.number_input("Enter standard carb:")
    std_bicarb = st.number_input("Enter standard bicarb:") 

    if std_carb is not None and std_bicarb is not None:
        data.loc[data['Sample name'] == 'Standard', 'Carb Deviation'] = \
            std_carb - data.loc[data['Sample name'] == 'Standard', 'Adj Carb'] # calculates bicarb deviation for standard samples
        data.loc[data['Sample name'] == 'Standard', 'BiCarb Deviation'] = \
            data.loc[data['Sample name'] == 'Standard', 'Adj BiCarb'] - std_bicarb # calculates bicarb deviation for standard samples

        data = data.reset_index(drop = True)
        data.fillna(0, inplace = True)

        # standards = data[data['Sample name'] == 'Standard']

        # Calculates and corrects deviation from standards for every sample
        idxs = data.index[data['System Name'] == 'Standard'] # index wherever there is a Standard sample
        for i in range(len(idxs)-1):
            first, second = idxs[i : i+2]
            first_val, second_val = data.loc[first, 'BiCarb Deviation'], data.loc[second, 'BiCarb Deviation']
            first_time, second_time = data.loc[first, 'time elapsed'], data.loc[second, 'time elapsed']

            # y = mx + b
            m = (second_val-first_val)/(second_time-first_time)
            b = second_val - m*second_time
            def adjust_deviation(time):
                return m*time + b
            rows_for_interpolation = data.loc[first:second, 'time elapsed']
            interpolated_values = rows_for_interpolation.apply(adjust_deviation)
            data.loc[first:second, 'BiCarb Deviation'] = interpolated_values

            first_val, second_val = data.loc[first, 'Carb Deviation'], data.loc[second, 'Carb Deviation']
            first_time, second_time = data.loc[first, 'time elapsed'], data.loc[second, 'time elapsed']
            # y = mx + b
            m = (second_val-first_val)/(second_time-first_time)
            b = second_val - m*second_time

            rows_for_interpolation = data.loc[first:second, 'time elapsed']
            interpolated_values = rows_for_interpolation.apply(adjust_deviation)
            data.loc[first:second, 'Carb Deviation'] = interpolated_values

        data['Adj BiCarb'] = data['Adj BiCarb'] - data['BiCarb Deviation']
        data['Adj Carb'] = data['Adj Carb'] + data['Carb Deviation']


        avg_data = data.groupby(['Subsample name', 'System Name']).mean()
        avg_data.reset_index(inplace=True)
        avg_data = avg_data[avg_data['Subsample name']!='6-25,8'] # removes standards from data 
        avg_data.drop(columns = ['Carb Deviation', 'BiCarb Deviation', 'time elapsed'], inplace = True)
        st.write('Averaged Data')
        st.write(avg_data)



    processing_choice = st.radio("Choose data processing type:", ('Upstream', 'Downstream'))

    if processing_choice == 'Upstream':
        st.write("Selected processing type: Upstream")
        avg_data['Molar Carb Conversion %'] = 100 * (avg_data['Adj BiCarb']/200.1)/(avg_data['Adj BiCarb']/200.1 + avg_data['wt% carb']/138.25)

        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(avg_data['Test time'], avg_data['Molar Carb Conversion %'], marker='o', label='Molar Carb Conversion %', color='tab:blue')
        ax1.set_xlabel("Test Time")
        ax1.set_ylabel("Molar Carb Conversion %", color='tab:blue')
        ax1.legend(loc='upper left')
        ax1.grid(color='black', linestyle='-', linewidth=0.3)

        st.sidebar.header("Graph Settings")
        title = st.sidebar.text_input("Graph Title", "Conversion and Molar Carb Conversion % Graph")

        ax1.set_title(title)
        fig.tight_layout()
        st.pyplot(fig)  


    elif processing_choice == 'Downstream':
        st.write("Selected processing type: Downstream")
        initial_bicarb = avg_data['Adj BiCarb'].max()
        avg_data['Molar Carb Conversion %'] = 100 * (avg_data['Adj BiCarb']/200.1)/(avg_data['Adj BiCarb']/200.1 + avg_data['wt% carb']/138.25)
        avg_data['Conversion %'] = (1-(avg_data['Adj BiCarb']/initial_bicarb))*100
        st.write(avg_data)

        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(avg_data['Test time'], avg_data['Conversion %'], marker='o', label='Conversion %', color='tab:blue')
        ax1.set_xlabel("Test Time")
        ax1.set_ylabel("Conversion %", color='tab:blue')
        ax1.grid(color='black', linestyle='-', linewidth=0.3)
        ax1.legend(loc='upper left')

        ax2 = ax1.twinx()
        ax2.plot(avg_data['Test time'], avg_data['Molar Carb Conversion %'], marker='^', label='Molar Carb Conversion %', color='tab:orange')
        ax2.set_ylabel("Molar Carb Conversion %", color='tab:orange')
        ax2.legend(loc='upper right')

        st.sidebar.header("Graph Settings")
        title = st.sidebar.text_input("Graph Title", "Conversion and Molar Carb Conversion % Graph")

        ax1.set_title(title)
        fig.tight_layout()
        st.pyplot(fig)       

    if st.button("Download Averaged Data as CSV"):
        csv = avg_data.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="averaged_data.csv">Download Averaged Data CSV</a>'
        st.markdown(href, unsafe_allow_html=True)