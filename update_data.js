const axios = require('axios');
const fs = require('fs');

const WEATHER_KEY = process.env.WEATHER_API_KEY;
const GOV_KEY = process.env.GOV_API_KEY;

const districts = ["Latur", "Pune", "Nashik", "Nagpur", "Jalgaon", "Satara", "Solapur", "Akola", "Amravati"];
const crops = ["Soybean", "Cotton", "Sugarcane", "Tur", "Onion", "Grapes"];

async function updateAgriData() {
    let finalData = {};
    const currentTime = new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" });

    for (let district of districts) {
        finalData[district] = {
            last_updated: currentTime,
            weather: {},
            crops: {}
        };

        // 1. Weather Update
        try {
            if (WEATHER_KEY) {
                const wUrl = `https://api.openweathermap.org/data/2.5/weather?q=${district},IN&units=metric&appid=${WEATHER_KEY}`;
                const wRes = await axios.get(wUrl);
                finalData[district].weather = {
                    temp: `${Math.round(wRes.data.main.temp)}°C`,
                    desc: wRes.data.weather[0].description,
                    humidity: `${wRes.data.main.humidity}%`,
                    rain_prob: wRes.data.rain ? "High Probability" : "Low/Moderate"
                };
            }
        } catch (e) {
            console.log(`Weather error for ${district}: ${e.message}`);
            finalData[district].weather = { temp: "30°C", desc: "No Data", humidity: "60%", rain_prob: "N/A" };
        }

        // 2. Mandi Price Update
        for (let crop of crops) {
            try {
                if (GOV_KEY) {
                    const govUrl = `https://api.data.gov.in/resource/9ef84268-d588-4dc4-82bd-de9791047b74?api-key=${GOV_KEY}&format=json&filters[state]=Maharashtra&filters[district]=${district}&filters[commodity]=${crop}`;
                    const govRes = await axios.get(govUrl);
                    
                    if (govRes.data.records && govRes.data.records.length > 0) {
                        const record = govRes.data.records[0];
                        finalData[district].crops[crop] = {
                            price: record.modal_price,
                            min_price: record.min_price,
                            max_price: record.max_price,
                            date: record.arrival_date,
                            status: "live"
                        };
                    } else {
                        finalData[district].crops[crop] = { price: "4500", date: "Check Local Mandi", status: "offline" };
                    }
                }
            } catch (e) {
                console.log(`Mandi error for ${district} - ${crop}: ${e.message}`);
                finalData[district].crops[crop] = { price: "N/A", date: "Error", status: "offline" };
            }
        }
    }

    fs.writeFileSync('data.json', JSON.stringify(finalData, null, 2));
    console.log(`Data successfully updated at ${currentTime}`);
}

updateAgriData();
