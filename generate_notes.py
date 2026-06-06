#!/usr/bin/env python
import json

# Extracted transcript text (cleaned)
transcript_text = """
Obesity is a complex health condition caused by multiple factors: excessive calorie intake,
socioeconomic pressures, environmental food design, and genetic hunger signals. Most people 
gradually become obese through small daily calorie excesses (like half a snickers bar daily), 
which compounds to 5kg of fat yearly. Traditional dieting approaches fail because people regain 
weight within 1-2 years due to biological mechanisms pulling them back to their fat baseline.
Hunger is primarily controlled by hormones, not willpower. Excess fat disrupts the hormonal 
orchestra, dysregulating hunger signals especially in overweight/obese individuals. GLP-1 
(Glucagon-like Peptide-1) is a natural hormone released after meals that controls appetite, 
regulates blood sugar, and slows digestion. Scientists developed synthetic GLP-1 drugs that 
amplify these signals.
The first artificial GLP-1 was approved in 2005 for diabetes and 2014 for obesity. The 
breakthrough came with semaglutide and tirzepatide (Ozempic and Mounjaro) - powerful GLP-1 
agonists lasting up to a week in the bloodstream, continuously suppressing appetite 24/7. 
Users feel satisfied sooner, eat less often, and experience dramatic psychological relief 
from food cravings. Dieting becomes effortless as biology changes behavior.
Weight loss results are exceptional: 10% in 3 months, 15% in 6 months, and 20%+ after a year 
- matching bariatric surgery outcomes. Health benefits are stunning: 20% stroke/heart attack 
risk reduction, 66% diabetes prevention, improved kidney/liver function, reduced inflammation, 
lower cancer risk, and potential Alzheimer's benefits. Drugs may also reduce alcohol, nicotine, 
cannabis, and opioid use. Side effects are generally mild (nausea, diarrhea) but can include 
serious issues like pancreatitis or gallbladder disease in under 5% of users.
Critical concerns include muscle loss from rapid weight loss without resistance training, and 
sustainability: about 25% regain significant weight, 20% regain all weight post-treatment. 
Long-term use may be necessary for many people. Newer generation drugs lack long-term data, 
though older GLP-1s show no major issues. These drugs aren't miracle cures - they remove 
appetite pressure to enable behavior change, but require lifestyle modifications to work.
Broader implications: If millions used GLP-1 drugs, obesity could drop 50% in 2 years, 
preventing 26M diabetes cases, 13M heart disease cases, and 5.5M premature deaths. Patents 
expiring soon will dramatically reduce costs and increase accessibility. Obstacles include 
supply shortages and current high prices. These drugs represent a major breakthrough in 
addressing obesity, but success depends on medical supervision, proper nutrition (including 
protein), resistance training, and sustainable lifestyle changes alongside medication use.
"""

timestamps = [
    {"time": "00:00", "title": "Introduction - Obesity Crisis"},
    {"time": "03:05", "title": "Why Traditional Diets Fail"},
    {"time": "04:05", "title": "The Role of Hunger Hormones"},
    {"time": "06:23", "title": "Ground News Sponsor"},
    {"time": "05:42", "title": "GLP-1 Hormone Explained"},
    {"time": "07:01", "title": "Artificial GLP-1 Drugs Development"},
    {"time": "08:15", "title": "Semaglutide and Tirzepatide (Ozempic/Mounjaro)"},
    {"time": "08:01", "title": "How GLP-1 Drugs Work in the Body"},
    {"time": "08:15", "title": "Psychological Impact of Appetite Suppression"},
    {"time": "08:32", "title": "Weight Loss Results - Miracle Drugs"},
    {"time": "09:53", "title": "Health Benefits Beyond Weight Loss"},
    {"time": "10:13", "title": "Cardiovascular and Metabolic Benefits"},
    {"time": "10:14", "title": "Additional Benefits - Addiction Reduction"},
    {"time": "10:06", "title": "Side Effects and Safety Concerns"},
    {"time": "10:40", "title": "Muscle Loss and Rapid Weight Loss Risks"},
    {"time": "11:21", "title": "Long-term Sustainability and Weight Regain"},
    {"time": "11:54", "title": "Realistic Expectations and Drug Limitations"},
    {"time": "12:44", "title": "Population-Level Impact Modeling"},
    {"time": "13:20", "title": "Cost, Supply, and Future Accessibility"},
    {"time": "13:48", "title": "Final Conclusions and Recommendations"},
]

key_points = [
    "Obesity develops through accumulated small calorie surpluses (e.g., 500 extra calories/day = 5kg fat/year) combined with genetic hunger factors and environmental food design",
    "Traditional diet success rates are extremely low because the body actively resists weight loss and hunger dysregulation persists even after losing weight",
    "GLP-1 (Glucagon-like Peptide-1) is a natural hormone that controls appetite, regulates blood sugar, and slows digestion; synthetic versions amplify these signals dramatically",
    "Semaglutide and tirzepatide (Ozempic/Mounjaro) are breakthrough drugs that last up to a week in the bloodstream, continuously suppressing appetite 24/7 without willpower",
    "Clinical results: 10% weight loss in 3 months, 15% in 6 months, 20%+ in a year - matching bariatric surgery outcomes for the first time",
    "Health benefits include 20% stroke/heart attack risk reduction, 66% diabetes prevention, improved kidney/liver function, reduced inflammation, potential Alzheimer's benefits, and improved fertility",
    "GLP-1 drugs may reduce alcohol, nicotine, cannabis, and opioid use by treating the underlying dysregulated hunger/craving signals, not just appetite for food",
    "Side effects are usually mild (nausea, diarrhea, constipation) but can be serious (pancreatitis, gallbladder disease, kidney problems) in under 5% of users requiring medical supervision",
    "Critical risk: without resistance training and adequate protein, users lose significant muscle mass during rapid weight loss, especially harmful for adults over 40",
    "Sustainability issue: approximately 25% regain significant weight and 20% regain all weight after stopping medication, requiring long-term use for many people",
    "These drugs remove appetite pressure to enable behavior change, but do not replace the need for sustainable lifestyle modifications, exercise, and proper nutrition",
    "Population modeling shows that widespread GLP-1 use could reduce obesity by 50% in 2 years and prevent 26M diabetes cases, 13M heart disease cases, and 5.5M premature deaths",
    "Current barriers: supply shortages and high prices; however, patent expirations will dramatically reduce costs and increase accessibility within years",
    "GLP-1 drugs are not for people seeking minor weight loss with no comorbidities - traditional approaches should be tried first before pharmaceutical intervention",
]

summary = """
GLP-1 drugs like semaglutide and tirzepatide represent a breakthrough in obesity treatment by addressing the biological root cause: dysregulated hunger hormones. These synthetic versions of the natural GLP-1 hormone provide continuous appetite suppression for up to a week, enabling weight loss without willpower by changing biology rather than relying on behavior alone. Clinical results are unprecedented - achieving 20% weight loss in a year, matching bariatric surgery outcomes for the first time and reducing stroke/heart attack risk by 20% and diabetes risk by 66%.

Traditional diets fail because obesity develops through accumulated calorie surpluses and genetic hunger factors, with the body actively resisting weight loss even after it occurs. GLP-1 drugs provide relief from "food noise" - the constant urge to eat - giving people a time window to establish healthier habits. However, they are not magic: rapid weight loss requires resistance training and adequate protein to prevent muscle loss, especially critical for adults over 40. Approximately 20-25% of people regain weight after stopping, suggesting long-term medication may be necessary for sustainable results.

Population modeling indicates widespread GLP-1 use could prevent 26 million diabetes cases and 5.5 million premature deaths. Beyond appetite suppression, these drugs show promise reducing alcohol, nicotine, cannabis, and opioid use through shared neurological mechanisms. Current barriers include supply shortages and high prices, but patent expirations will dramatically reduce costs. While side effects are usually mild (nausea, diarrhea), serious complications like pancreatitis occur in under 5% of users. Success requires medical supervision, ongoing lifestyle changes, and realistic expectations - these drugs enable weight loss but don't replace the need for sustained behavioral modification and exercise.
"""

output = {
    "summary": summary.strip(),
    "key_points": key_points,
    "timestamps": timestamps
}

print(json.dumps(output, indent=2))
