// Copyright (c) OpenMMLab. All rights reserved.

// clang-format off
#include "catch.hpp"
// clang-format on

#include "core/model.h"
#include "core/net.h"
#include "test_resource.h"

using namespace mmdeploy;

TEST_CASE("test trt net", "[trt_net]") {
  auto& gResource = MMDeployTestResources::Get();
  auto model_list = gResource.LocateModelResources("mmcls/trt");
  REQUIRE(!model_list.empty());

  Model model(model_list.front());
  REQUIRE(model);

  auto backend("tensorrt");
  auto creator = Registry<Net>::Get().GetCreator(backend);
  REQUIRE(creator);

  Device device{"cuda"};
  auto stream = Stream::GetDefault(device);
  Value net_config{{"context", {{"device", device}, {"model", model}, {"stream", stream}}},
                   {"name", model.meta().models[0].name}};
  auto net = creator->Create(net_config);
  REQUIRE(net);
}