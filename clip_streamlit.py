import streamlit as st
import torch
import torch.nn as nn
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
import io

#config
BASE_CLIP_MODEL = "openai/clip-vit-base-patch32"
OUTPUT_MODEL_PATH = "clip_finetuned_youtube_virality.pt"

# Page setup
st.set_page_config(page_title="ViralPredictor", page_icon="🏆", layout="wide")

#model
class CLIPRegressor(nn.Module):
    def __init__(self, clip_model):
        super().__init__()
        self.clip = clip_model
        self.regressor = nn.Sequential(
            nn.Linear(512 + 512 + 1, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, pixel_values, input_ids, attention_mask, age):
        outputs = self.clip(
            pixel_values=pixel_values,
            input_ids=input_ids,
            attention_mask=attention_mask,
        )
        image_embeds = outputs.image_embeds
        text_embeds = outputs.text_embeds
        age = age.unsqueeze(1)
        combined = torch.cat((image_embeds, text_embeds, age), dim=-1)
        combined = nn.functional.layer_norm(combined, combined.shape[-1:])
        preds = self.regressor(combined).squeeze(-1)
        return preds

# load model
@st.cache_resource
def load_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading model on {device}...")
    
    clip_model = CLIPModel.from_pretrained(BASE_CLIP_MODEL).to(device)
    processor = CLIPProcessor.from_pretrained(BASE_CLIP_MODEL)
    model = CLIPRegressor(clip_model).to(device)
    
    try:
        state_dict = torch.load(OUTPUT_MODEL_PATH, map_location=device)
        model.load_state_dict(state_dict, strict=False)
        model.eval()
    except FileNotFoundError:
        st.warning(f"⚠️ Model file '{OUTPUT_MODEL_PATH}' not found. Using random weights for demo.")
        model.eval()
        
    return model, processor, device

# Load resources
model, processor, device = load_model()

# ui
if 'candidates' not in st.session_state:
    st.session_state.candidates = [{"id": 0}]

def add_candidate():
    st.session_state.candidates.append({"id": len(st.session_state.candidates)})

def remove_candidate(idx):
    if len(st.session_state.candidates) > 1:
        st.session_state.candidates.pop(idx)

#input
with st.container():
    st.subheader("Upload Videos")
    
    inputs = []
    
    # Dynamic Input Fields
    for idx, candidate in enumerate(st.session_state.candidates):
        with st.expander(f"Option {idx + 1}", expanded=True):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                uploaded_file = st.file_uploader(f"Thumbnail {idx+1}", type=["jpg", "png", "jpeg"], key=f"img_{idx}")
                if uploaded_file:
                    st.image(uploaded_file, use_container_width=True)
            
            with col2:
                caption = st.text_input(f"Video Title {idx+1}", placeholder="e.g., I SURVIVED 50 HOURS...", key=f"txt_{idx}")
            
            if uploaded_file and caption:
                inputs.append({"image": uploaded_file, "caption": caption, "idx": idx})

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        st.button("➕ Add Another Variant", on_click=add_candidate)

# prediction
if st.button("🚀 Predict Virality", type="primary", use_container_width=True):
    if not inputs:
        st.error("Please upload an image and enter a title for at least one option.")
    else:
        results = []
        progress_bar = st.progress(0)
        
        for i, item in enumerate(inputs):
            # Process Image
            image_bytes = item['image'].getvalue()
            img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            # Prepare Inputs
            model_inputs = processor(
                images=img,
                text=item['caption'],
                return_tensors="pt",
                padding="max_length",
                max_length=77,
                truncation=True,
            )
            
            pixel_values = model_inputs['pixel_values'].to(device)
            input_ids = model_inputs['input_ids'].to(device)
            attention_mask = model_inputs['attention_mask'].to(device)
            age = torch.zeros(pixel_values.size(0), device=device)
            
            # Predict
            with torch.no_grad():
                pred_log10 = model(pixel_values, input_ids, attention_mask, age).item()
            
            predicted_views = 10 ** pred_log10
            results.append({
                "image": item['image'],
                "caption": item['caption'],
                "views": predicted_views
            })
            progress_bar.progress((i + 1) / len(inputs))
            
        # Sort results
        results.sort(key=lambda x: x['views'], reverse=True)
        max_views = results[0]['views']
        
        # displaying results
        st.divider()
        st.subheader("📊 Analysis Results")
        
        # Winner Display
        best = results[0]
        st.success(f"**WINNER CHOICE:** {best['caption']}")
        
        col_win1, col_win2 = st.columns([1, 1])
        with col_win1:
            st.image(best['image'], caption="Best Thumbnail")
        with col_win2:
            st.metric(label="Virality Potential", value="Highest", delta="Best Option")
            st.info("This combination is predicted to generate the most engagement.")

        st.write("---")
        st.write("### Detailed Breakdown")

        for res in results:
            score = int((res['views'] / max_views) * 100)
            
            c1, c2, c3 = st.columns([1, 4, 1])
            with c1:
                st.image(res['image'], width=100)
            with c2:
                st.write(f"**{res['caption']}**")
                if score == 100:
                    st.progress(score)
                else:
                    st.progress(score)
            with c3:
                st.metric("Score", f"{score}/100")